"""Every registered admin operation must reject a signed-in ordinary member."""
import re
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_member


def test_all_admin_endpoints_reject_member_before_validation_or_storage():
    app = create_app(Settings(_env_file=None, environment='test'))
    app.dependency_overrides[require_member] = lambda: {'id': str(uuid4()), 'role': 'member'}
    checked = 0
    with TestClient(app) as client:
        for template, operations in app.openapi()['paths'].items():
            if not template.startswith('/api/v1/admin/'):
                continue
            path = re.sub(r'\{([^}]+)\}', lambda match:
                'resources' if match[1] == 'kind' else
                'topic' if match[1] in {'node_type', 'node_kind'} else str(uuid4()), template)
            for method in operations:
                if method not in {'get', 'post', 'patch', 'put', 'delete'}:
                    continue
                response = client.request(method, path, json={} if method != 'get' else None)
                assert response.status_code == 403, method.upper() + ' ' + template + ': ' + str(response.status_code)
                checked += 1
    assert checked > 50, 'Admin route coverage unexpectedly shrank'
