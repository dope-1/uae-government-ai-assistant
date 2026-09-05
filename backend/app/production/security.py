from __future__ import annotations

from app.core.config import Settings


def validate_production_settings(settings: Settings) -> None:
    """Fail fast on a small set of dangerous production configurations."""

    if settings.app_env.casefold() != "production":
        return

    problems: list[str] = []
    if "*" in settings.cors_origins:
        problems.append("CORS_ORIGINS must not contain '*' in production")
    if "*" in settings.trusted_hosts:
        problems.append("TRUSTED_HOSTS must not contain '*' in production")
    if not settings.rate_limit_enabled:
        problems.append("RATE_LIMIT_ENABLED must remain true in production")
    if not settings.security_headers_enabled:
        problems.append("SECURITY_HEADERS_ENABLED must remain true in production")
    if "uae_ai_local" in settings.database_url:
        problems.append("DATABASE_URL still contains the local development credential")
    if settings.ops_metrics_enabled and not settings.ops_metrics_token:
        problems.append("OPS_METRICS_TOKEN is required when ops metrics are enabled")

    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
