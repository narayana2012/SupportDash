"""Process settings, read from the environment and an optional .env file.

Secrets are SecretStr. Dumping settings with model_dump() never shows a
secret or a URL password. Code that connects to a service reads the attributes.
"""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_serializer, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REDACTED = "**********"


def redact_url(value: str) -> str:
    """Replace the password in a URL's userinfo. Other parts are unchanged."""
    if not value:
        return value
    parts = urlsplit(value)
    if parts.password is None:
        return value
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{parts.username}:{REDACTED}@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime
    demo_mode: bool = False
    environment: Literal["local", "test", "staging", "prod"] = "local"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    log_level: str = "INFO"

    # Auth (HS256). effective_jwt_secret prefers the Supabase secret when set.
    jwt_secret: SecretStr = SecretStr("")
    supabase_jwt_secret: SecretStr | None = None

    # Data stores
    database_url: str = "sqlite+aiosqlite:///./data/support.db"
    checkpoint_db_path: str = "./data/checkpoints.db"
    redis_url: str = ""
    use_fake_redis: bool = False

    # LLM and embeddings
    llm_provider: str = "fake"
    llm_api_key: SecretStr | None = None
    llm_model: str = ""
    embedding_provider: str = "fake"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=384, gt=0)

    # Vector store
    vector_store: Literal["memory", "qdrant"] = "memory"
    qdrant_url: str = ""
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "supportdash_knowledge"

    # Policy and limits
    approval_required_for_refunds: bool = True
    max_refund_without_approval: int = Field(default=0, ge=0)
    tool_timeout_seconds: float = Field(default=10.0, gt=0)
    rate_limit_per_minute: int = Field(default=120, ge=1)
    sample_data_dir: str = "./sample_data"

    # Observability (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_project: str = "supportdash-support"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _demo_not_in_prod(self) -> "Settings":
        if self.environment == "prod" and self.demo_mode:
            raise ValueError("DEMO_MODE must be false when ENVIRONMENT=prod")
        return self

    @property
    def effective_jwt_secret(self) -> SecretStr:
        if self.supabase_jwt_secret is not None and self.supabase_jwt_secret.get_secret_value():
            return self.supabase_jwt_secret
        return self.jwt_secret

    @field_serializer("jwt_secret", "supabase_jwt_secret", "llm_api_key", "qdrant_api_key",
                      "langchain_api_key", when_used="always")
    def _redact_secret(self, value: SecretStr | None) -> str | None:
        if value is None:
            return None
        return REDACTED if value.get_secret_value() else ""

    @field_serializer("database_url", "redis_url", "qdrant_url", when_used="always")
    def _redact_url_fields(self, value: str) -> str:
        return redact_url(value)


@lru_cache
def get_settings() -> Settings:
    """Cached for the process. Restart the server after changing .env."""
    return Settings()
