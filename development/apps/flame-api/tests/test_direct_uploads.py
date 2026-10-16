from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from PIL import Image
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_admin
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.resources.direct_uploads import Admission, Ticket, cipher
from app.modules.functional.resources.models import ResourceUpload
from app.modules.functional.curriculum.import_models import CurriculumImport
from app.modules.functional.bulk_transfer.models import BulkImport
from test_curriculum_workspace import isolated_client


def cloud_settings():
    return Settings(_env_file=None, environment='test', resource_storage_backend='supabase',
                    resource_storage_bucket='private', supabase_url='https://storage.example.test',
                    supabase_secret_key='synthetic-server-secret', session_encryption_key=Fernet.generate_key().decode())


@pytest.mark.parametrize('values', [
    {'purpose': 'resource', 'filename': 'demo.html', 'mime_type': 'text/html', 'byte_size': 2 * 1024 * 1024 + 1},
    {'purpose': 'resource', 'filename': '../demo.png', 'mime_type': 'image/png', 'byte_size': 10},
    {'purpose': 'resource', 'filename': 'demo.png', 'mime_type': 'text/html', 'byte_size': 10},
    {'purpose': 'curriculum', 'filename': 'book.xlsx', 'mime_type': '', 'byte_size': 10},
    {'purpose': 'bulk', 'kind': 'resources', 'filename': 'book.exe', 'mime_type': '', 'byte_size': 10},
])
def test_admission_rejects_invalid_formats_limits_and_targets(values):
    with pytest.raises(ValidationError):
        Admission(**values, sha256='0' * 64)


def test_expired_ticket_is_rejected_before_database_or_storage():
    settings = cloud_settings()
    app = create_app(settings)
    app.dependency_overrides[require_admin] = lambda: {'id': str(uuid4()), 'role': 'admin'}
    ticket = Ticket(version=1, id=uuid4(), owner='synthetic', admission=Admission(
        purpose='resource', filename='demo.png', mime_type='image/png', byte_size=10, sha256='0' * 64))
    expired = cipher(settings).encrypt_at_time(ticket.model_dump_json().encode(), 1).decode()
    with TestClient(app) as client:
        result = client.post('/api/v1/admin/transfers/complete', json={'ticket': expired})
    assert result.status_code == 410
    assert result.json()['error']['code'] == 'upload_ticket_expired_or_invalid'


@contextmanager
def storage_fixture(monkeypatch, client):
    objects = {}
    original = httpx.Client
    config = cloud_settings()
    config.database_url = client.app.state.settings.database_url
    client.app.state.settings = config
    def handle(request):
        path = request.url.path.removeprefix('/storage/v1')
        if path.startswith('/object/upload/sign/'):
            assert request.headers.get('x-upsert') != 'true'
            return httpx.Response(200, json={'url': path + '?token=synthetic-upload'})
        if path.startswith('/object/sign/'):
            key = path.removeprefix('/object/sign/private/')
            return httpx.Response(200, json={'signedURL': path + '?token=synthetic-read'}) if key in objects else httpx.Response(404)
        if path == '/object/private' and request.method == 'DELETE':
            import json
            for key in json.loads(request.content)['prefixes']:
                objects.pop(key, None)
            return httpx.Response(200, json=[])
        key = path.removeprefix('/object/private/')
        if request.method == 'POST':
            assert request.headers.get('x-upsert') == 'false'
            if key in objects: return httpx.Response(409)
            objects[key] = request.read()
            return httpx.Response(200, json={})
        if request.method == 'HEAD': return httpx.Response(200 if key in objects else 400)
        return httpx.Response(200, content=objects[key]) if key in objects else httpx.Response(404)
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    yield objects


def admit(client, objects, data, **target):
    request = {'byte_size': len(data), 'sha256': sha256(data).hexdigest(), **target}
    response = client.post('/api/v1/admin/transfers/authorize', json=request)
    assert response.status_code == 200, response.text
    capsule = response.json()['ticket']
    ticket = Ticket.model_validate_json(cipher(client.app.state.settings).decrypt(capsule.encode()))
    objects['staged-uploads/' + ticket.id.hex] = data
    return capsule, ticket.id


@pytest.mark.db_integration
def test_resource_finalize_replay_hash_and_owner_isolation(monkeypatch):
    with isolated_client() as client, storage_fixture(monkeypatch, client) as objects:
        out = BytesIO(); Image.new('RGB', (4, 4), 'blue').save(out, 'PNG'); data = out.getvalue()
        capsule, upload_id = admit(client, objects, data, purpose='resource', filename='tiny.png', mime_type='image/png')
        first = client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule})
        assert first.status_code == 200, first.text
        assert first.json()['upload_id'] == str(upload_id)
        assert objects['resource-uploads/' + upload_id.hex + '.png'] == data
        assert 'staged-uploads/' + upload_id.hex not in objects
        assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule}).json() == first.json()
        with client.app.state.database.session() as db:
            assert db.query(ResourceUpload).filter_by(id=upload_id).count() == 1
        capsule2, second_id = admit(client, objects, data, purpose='resource', filename='tiny.png', mime_type='image/png')
        objects['staged-uploads/' + second_id.hex] = b'x' * len(data)
        assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule2}).status_code == 422
        assert 'resource-uploads/' + second_id.hex + '.png' not in objects
        stranger = uuid4()
        with client.app.state.database.session() as db, db.begin(): db.add(StudentProfile(id=stranger, auth_subject=str(stranger)))
        client.app.dependency_overrides[require_admin] = lambda: {'id': str(stranger), 'role': 'admin'}
        assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule}).status_code == 404


@pytest.mark.db_integration
def test_curriculum_and_bulk_replay_use_durable_existing_records(monkeypatch):
    with isolated_client() as client, storage_fixture(monkeypatch, client) as objects:
        curriculum = client.post('/api/v1/admin/curricula', json={'code': 'direct-' + uuid4().hex[:8], 'name': 'Direct fixture'}).json()
        book = Workbook(); sheet = book.active; sheet.title = 'Curriculum'; sheet.append(['Curriculum Code', 'Level', 'Subject', 'Domain', 'Category', 'Topic', 'Subtopic'])
        sheet.append([curriculum['code'], 'Grade 1', 'Science', 'Motion', '', 'Gravity', 'Falling'])
        buffer = BytesIO(); book.save(buffer)
        capsule, identity = admit(client, objects, buffer.getvalue(), purpose='curriculum', curriculum_id=curriculum['id'], filename='book.xlsx', mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        first = client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule})
        assert first.status_code == 200, first.text
        assert first.json()['import_id'] == str(identity)
        assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule}).json()['import_id'] == str(identity)
        with client.app.state.database.session() as db:
            assert db.query(CurriculumImport).filter_by(id=identity).count() == 1
        book = Workbook(); sheet = book.active; sheet.title = 'Records'; sheet.append(['name']); sheet.append(['Synthetic tutor'])
        buffer = BytesIO(); book.save(buffer)
        capsule, identity = admit(client, objects, buffer.getvalue(), purpose='bulk', kind='teachers', filename='teachers.xlsx', mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        first = client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule})
        assert first.status_code == 200, first.text
        assert first.json()['id'] == str(identity)
        assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule}).json() == first.json()
        with client.app.state.database.session() as db:
            assert db.query(BulkImport).filter_by(id=identity).count() == 1


@pytest.mark.db_integration
def test_private_export_returns_metadata_and_signed_artifact(monkeypatch):
    with isolated_client() as client, storage_fixture(monkeypatch, client) as objects:
        response = client.post('/api/v1/admin/transfers/export', json={
            'purpose': 'bulk', 'kind': 'teachers', 'action': 'template'})
        assert response.status_code == 200, response.text
        assert response.json()['expires_in'] == 300
        assert response.json()['filename'].endswith('.xlsx')
        assert any(key.startswith('transfer-exports/') for key in objects)
        assert len(response.content) < 5000


@pytest.mark.db_integration
def test_direct_upload_rejects_missing_oversized_and_invalid_media(monkeypatch):
    with isolated_client() as client, storage_fixture(monkeypatch, client) as objects:
        for data, replacement, expected in ((b'not-a-png', None, 422),
                                             (b'file', b'oversized-file', 413),
                                             (b'file', b'', 409)):
            capsule, identity = admit(client, objects, data, purpose='resource', filename='tiny.png', mime_type='image/png')
            key = 'staged-uploads/' + identity.hex
            if replacement == b'':
                objects.pop(key)
            elif replacement is not None:
                objects[key] = replacement
            assert client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule}).status_code == expected
            with client.app.state.database.session() as db:
                assert db.get(ResourceUpload, identity) is None


@pytest.mark.db_integration
def test_completed_receipt_survives_concurrent_insert_error(monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from app.modules.functional.resources import router as resources
    with isolated_client() as client, storage_fixture(monkeypatch, client) as objects:
        out = BytesIO(); Image.new('RGB', (4, 4), 'blue').save(out, 'PNG')
        capsule, identity = admit(client, objects, out.getvalue(), purpose='resource', filename='tiny.png', mime_type='image/png')
        original = resources.store_upload
        def concurrent_winner(*args, **kwargs):
            original(*args, **kwargs)
            raise IntegrityError('synthetic conflict', None, Exception('concurrent winner'))
        monkeypatch.setattr(resources, 'store_upload', concurrent_winner)
        response = client.post('/api/v1/admin/transfers/complete', json={'ticket': capsule})
        assert response.status_code == 200, response.text
        assert response.json()['upload_id'] == str(identity)
        assert objects['resource-uploads/' + identity.hex + '.png'] == out.getvalue()


@pytest.mark.db_integration
def test_live_large_direct_private_upload_and_export():
    """Opt-in real bucket check; only synthetic objects and rolled-back UUID rows."""
    import logging
    import os
    from random import Random
    from urllib.parse import urlsplit
    from app.modules.functional.resources.storage import ResourceStorage
    if os.environ.get('FLAME_RUN_STORAGE_TESTS') != '1':
        pytest.skip('Set FLAME_RUN_STORAGE_TESTS=1 for synthetic live private storage checks')
    settings = Settings().model_copy(update={'environment': 'test', 'resource_storage_backend': 'supabase',
                                            'resource_storage_bucket': 'flame-resources'})
    keys = []
    out = BytesIO()
    Image.frombytes('RGB', (1280, 1280), Random(777).randbytes(1280 * 1280 * 3)).save(out, 'PNG')
    data = out.getvalue()
    assert len(data) > 4_500_000
    logging.getLogger('httpx').setLevel(logging.WARNING)
    with isolated_client() as client:
        client.app.state.settings = settings
        token = (settings.supabase_secret_key or settings.supabase_service_role_key).get_secret_value()
        headers = {'apikey': token, 'Authorization': 'Bearer ' + token}
        origin = settings.supabase_url + '/storage/v1'
        try:
            response = client.post('/api/v1/admin/transfers/authorize', json={
                'purpose': 'resource', 'filename': 'synthetic-large.png', 'mime_type': 'image/png',
                'byte_size': len(data), 'sha256': sha256(data).hexdigest()})
            assert response.status_code == 200, 'Admission HTTP ' + str(response.status_code)
            permit = response.json()
            ticket = Ticket.model_validate_json(cipher(settings).decrypt(permit['ticket'].encode()))
            keys.extend(['staged-uploads/' + ticket.id.hex, 'resource-uploads/' + ticket.id.hex + '.png'])
            with httpx.Client(timeout=120, follow_redirects=False) as storage:
                uploaded = storage.put(permit['upload_url'], headers={'content-type': 'application/octet-stream', 'x-upsert': 'false'}, content=data)
                assert uploaded.status_code in (200, 201), 'Storage PUT HTTP ' + str(uploaded.status_code)
            first = client.post('/api/v1/admin/transfers/complete', json={'ticket': permit['ticket']})
            assert first.status_code == 200, 'Completion HTTP ' + str(first.status_code)
            assert first.json()['byte_size'] == len(data) and len(first.content) < 5000
            assert client.post('/api/v1/admin/transfers/complete', json={'ticket': permit['ticket']}).json() == first.json()
            with TemporaryDirectory() as directory:
                from pathlib import Path
                copied = Path(directory) / 'verified.png'
                ResourceStorage(settings).download_to(keys[1], copied, len(data))
                assert sha256(copied.read_bytes()).digest() == sha256(data).digest()
            artifact = client.post('/api/v1/admin/transfers/export', json={'purpose': 'bulk', 'kind': 'teachers', 'action': 'template'})
            assert artifact.status_code == 200, 'Export HTTP ' + str(artifact.status_code)
            relative = urlsplit(artifact.json()['url']).path.split('/object/sign/flame-resources/', 1)[1]
            keys.append(relative)
            with httpx.Client(timeout=20, follow_redirects=False) as storage:
                downloaded = storage.get(artifact.json()['url'])
                assert downloaded.status_code == 200 and downloaded.content.startswith(b'PK')
        finally:
            with httpx.Client(timeout=20, follow_redirects=False) as storage:
                for key in keys:
                    storage.request('DELETE', origin + '/object/flame-resources', headers=headers, json={'prefixes': [key]})
                    absent = storage.get(origin + '/object/flame-resources/' + key, headers=headers)
                    assert absent.status_code in (400, 404), 'Synthetic object cleanup unconfirmed'
