from typing import Literal
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLAME_", env_file=".env", extra="ignore",
    )
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr | None = None
    database_connect_timeout: int = Field(default=3, ge=1, le=30)
    deletion_receipt_retention_days: int = Field(default=30, ge=1, le=365)
    supabase_url: str | None = None
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_secret_key: SecretStr | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_secret: SecretStr | None = None
    session_encryption_key: SecretStr | None = None
    web_origin: str | None = None
    bff_shared_key: SecretStr | None = None
    google_sheets_credentials_file: str | None = None
    google_sheets_credentials_json: SecretStr | None = None
    resource_storage_backend: Literal["local", "supabase"] = "local"
    resource_local_dir: str = ".private-resources"
    resource_storage_bucket: str | None = None
    resource_allowed_hosts: str = ""
    resource_youtube_api_key: SecretStr | None = None
    resource_vimeo_api_token: SecretStr | None = None
    resource_local_delivery_origin: str = "http://127.0.0.1:8000"
    resource_recommendation_count: int = Field(default=3, ge=0, le=10)
    teacher_recommendation_count: int = Field(default=2, ge=0, le=5)
    teacher_recommendation_every_n_turns: int = Field(default=1, ge=1, le=20)
    llm_daily_request_limit: int = Field(default=100, ge=1, le=1000)
    llm_openai_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: int = Field(default=12, ge=1, le=20)
    llm_max_output_tokens: int = Field(default=1500, ge=100, le=1500)

    @model_validator(mode="after")
    def validate_database(self):
        if bool(self.llm_openai_api_key) != bool(self.llm_model):
            raise ValueError("LLM key and model must be configured together")
        if self.environment == "production" and self.database_url is None:
            raise ValueError("Database configuration is required in production")
        if self.environment == "production" and not all((self.supabase_url, self.supabase_anon_key, self.supabase_secret_key or self.supabase_service_role_key, self.session_encryption_key, self.web_origin, self.bff_shared_key)):
            raise ValueError("Identity and web origin configuration is required in production")
        if self.environment == "production" and (self.resource_storage_backend != "supabase" or not self.resource_storage_bucket):
            raise ValueError("Private durable resource storage is required in production")
        if self.supabase_url and (not self.supabase_url.startswith("https://") or self.supabase_url.endswith("/")):
            raise ValueError("Supabase URL must be HTTPS without a trailing slash")
        if self.database_url:
            try:
                url = make_url(self.database_url.get_secret_value())
                valid = (
                    url.drivername == "postgresql+psycopg"
                    and bool(url.host) and bool(url.database)
                )
            except Exception:
                valid = False
            if not valid:
                raise ValueError("Expected a PostgreSQL psycopg URL with host and database")
        return self





