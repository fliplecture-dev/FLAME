import json
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.functional.bulk_transfer import google_sheets


def test_hosted_secret_credentials_override_local_path_without_file_access(monkeypatch):
    info = {'type': 'service_account', 'token_uri': 'https://oauth2.googleapis.com/token',
            'client_email': 'synthetic@example.test', 'private_key': 'synthetic-private-key'}
    settings = Settings(_env_file=None, google_sheets_credentials_json=json.dumps(info),
                        google_sheets_credentials_file='nonexistent-local-path.json')
    assert 'synthetic-private-key' not in repr(settings)
    seen = []
    monkeypatch.setattr(google_sheets.Credentials, 'from_service_account_info',
                        lambda value, scopes: seen.append((value, scopes)) or SimpleNamespace(service_account_email=value['client_email']))
    assert google_sheets.credentials(settings).service_account_email == info['client_email']
    assert seen == [(info, ['https://www.googleapis.com/auth/spreadsheets'])]


@pytest.mark.parametrize('raw', ['not-json', '[]', '{}',
    '{"type":"service_account","token_uri":"https://untrusted.example.test/token"}'])
def test_invalid_hosted_credentials_return_safe_error(raw):
    from fastapi import HTTPException
    settings = Settings(_env_file=None, google_sheets_credentials_json=SecretStr(raw))
    with pytest.raises(HTTPException) as error:
        google_sheets.credentials(settings)
    assert error.value.status_code == 503
    assert raw not in str(error.value.detail)
