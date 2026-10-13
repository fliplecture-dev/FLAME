"""Supabase admin credential handling for confirmed account deletion."""
from unittest.mock import patch
from uuid import uuid4
import httpx
from app.core.config import Settings
from app.modules.data_lifecycle.service import delete_provider_user


def test_current_secret_key_uses_api_key_header_only():
    settings = Settings(_env_file=None, supabase_url="https://sample.supabase.co",
                        supabase_secret_key="sb_secret_test", supabase_service_role_key="legacy-test")
    with patch("app.modules.data_lifecycle.service.httpx.delete", return_value=httpx.Response(204)) as request:
        assert delete_provider_user(settings, str(uuid4()))
    headers = request.call_args.kwargs["headers"]
    assert headers == {"apikey": "sb_secret_test"}


def test_legacy_service_role_key_keeps_bearer_header():
    settings = Settings(_env_file=None, supabase_url="https://sample.supabase.co",
                        supabase_service_role_key="legacy-test")
    with patch("app.modules.data_lifecycle.service.httpx.delete", return_value=httpx.Response(200)) as request:
        assert delete_provider_user(settings, str(uuid4()))
    assert request.call_args.kwargs["headers"] == {
        "apikey": "legacy-test", "Authorization": "Bearer legacy-test"}
