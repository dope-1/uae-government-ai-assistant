import pytest

from app.core.config import Settings
from app.production.security import validate_production_settings


def test_local_settings_do_not_require_production_token() -> None:
    validate_production_settings(Settings(app_env="local", ops_metrics_token=None))


def test_production_settings_reject_insecure_defaults() -> None:
    settings = Settings(
        app_env="production",
        cors_origins="*",
        trusted_hosts="*",
        ops_metrics_token=None,
    )
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        validate_production_settings(settings)


def test_production_settings_accept_hardened_values() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://app:secret@db.internal:5432/uae_ai",
        cors_origins="https://assistant.example",
        trusted_hosts="assistant.example",
        ops_metrics_token="test-ops-token",
    )
    validate_production_settings(settings)
