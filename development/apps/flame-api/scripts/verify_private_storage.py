"""Opt-in private bucket and synthetic-object checks; never edits catalogue rows."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
from PIL import Image

from app.core.config import Settings
from app.modules.resources.storage import ResourceStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--create-bucket', action='store_true')
    parser.add_argument('--bucket', default='flame-resources')
    args = parser.parse_args()
    if not args.execute:
        print('No storage writes made. Use --execute for synthetic-object checks.')
        return
    if args.bucket != 'flame-resources':
        parser.error('This MVP probe is scoped to the flame-resources bucket.')
    settings = Settings()
    secret = settings.supabase_secret_key or settings.supabase_service_role_key
    if not settings.supabase_url or not secret:
        raise SystemExit('Supabase server configuration is missing.')
    token = secret.get_secret_value()
    headers = {'apikey': token, 'Authorization': 'Bearer ' + token}
    origin = settings.supabase_url + '/storage/v1'
    uploaded = []
    checks = {}
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        buckets = client.get(origin + '/bucket', headers=headers)
        if buckets.status_code != 200:
            raise SystemExit('Bucket inventory unavailable: HTTP ' + str(buckets.status_code))
        bucket = next((row for row in buckets.json() if row['id'] == args.bucket), None)
        created = False
        if bucket is None:
            if not args.create_bucket:
                raise SystemExit('Private bucket is missing. Provision it before verification.')
            response = client.post(origin + '/bucket', headers=headers,
                                   json={'id': args.bucket, 'name': args.bucket, 'public': False})
            if response.status_code not in (200, 201):
                raise SystemExit('Private bucket creation failed: HTTP ' + str(response.status_code))
            created = True
            response = client.get(origin + '/bucket/' + args.bucket, headers=headers)
            if response.status_code != 200:
                raise SystemExit('Created bucket could not be verified.')
            bucket = response.json()
        if bucket.get('public') is not False:
            raise SystemExit('Refusing a public bucket.')
        cloud = settings.model_copy(update={'resource_storage_backend': 'supabase',
                                            'resource_storage_bucket': args.bucket})
        storage = ResourceStorage(cloud)
        try:
            with TemporaryDirectory() as folder:
                png = Path(folder) / 'synthetic.png'
                Image.new('RGB', (4, 4), 'blue').save(png)
                html = Path(folder) / 'synthetic.html'
                html.write_text('<!doctype html><html><head><title>Storage probe</title></head><body><p>Synthetic test.</p></body></html>', encoding='utf-8')
                for source, mime in ((png, 'image/png'), (html, 'text/html')):
                    key = storage.new_key(source.suffix)
                    storage.put(key, source, mime)
                    uploaded.append(key)
                    assert storage.exists(key), 'Uploaded object is missing'
                    private = client.get(origin + '/object/public/' + args.bucket + '/' + key)
                    assert private.status_code != 200, 'Object unexpectedly public'
                    checks[source.suffix + '_anonymous_blocked'] = True
                    if source.suffix == '.html':
                        assert storage.read_document(key, 2 * 1024 * 1024) == source.read_bytes()
                        checks['html_authenticated_read'] = True
                    else:
                        signed = storage.signed_url(uuid4(), key, 0, '')
                        response = client.get(signed)
                        assert response.status_code == 200 and response.content == source.read_bytes()
                        checks['image_signed_delivery'] = True
        finally:
            # Only opaque keys created by this probe are removed; local files and real assets are untouched.
            for key in uploaded:
                storage.delete(key)
                response = client.get(origin + '/object/' + args.bucket + '/' + key, headers=headers)
                assert response.status_code != 200, 'Synthetic object cleanup unconfirmed'
        result = {'date': datetime.now(timezone.utc).isoformat(), 'bucket': args.bucket,
                  'private': True, 'bucket_created': created, 'checks': checks,
                  'synthetic_objects_cleaned': len(uploaded), 'catalogue_mutations': 0,
                  'local_backend_changed': False}
        destination = Path(__file__).resolve().parents[4] / 'work' / 'b9-private-storage-check.json'
        destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
