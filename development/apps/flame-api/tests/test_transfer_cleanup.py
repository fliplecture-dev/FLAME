from datetime import datetime, timezone
import json

import httpx

from scripts.purge_transfer_artifacts import purge
from test_direct_uploads import cloud_settings


def test_cleanup_retains_fresh_unknown_and_updated_objects_and_never_visits_assets():
    calls, deleted = [], []
    def handle(request):
        body = json.loads(request.content)
        calls.append(request.url.path)
        if request.method == 'DELETE':
            deleted.extend(body['prefixes'])
            return httpx.Response(200, json=[])
        prefix = body['prefix']
        assert prefix in {'staged-uploads', 'transfer-exports'}
        suffix = '.xlsx' if prefix == 'transfer-exports' else ''
        def row(name, updated='2026-10-10T00:00:00Z'):
            return {'id': name, 'name': name, 'created_at': '2026-10-10T00:00:00Z', 'updated_at': updated}
        return httpx.Response(200, json=[row('a' * 32 + suffix), row('b' * 32 + suffix, '2026-10-14T00:00:00Z'),
                                        row('unrecognized.xlsx'), row('c' * 32 + suffix, 'invalid')])
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        arguments = {'now': datetime(2026, 10, 14, 12, tzinfo=timezone.utc)}
        assert purge(cloud_settings(), client, **arguments)['expired_candidates'] == 2
        assert not deleted
        assert purge(cloud_settings(), client, execute=True, **arguments)['removed'] == 2
    assert deleted == ['staged-uploads/' + 'a' * 32, 'transfer-exports/' + 'a' * 32 + '.xlsx']
    assert all('resource-uploads' not in path for path in calls)
