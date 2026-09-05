from __future__ import annotations

from typing import Any

from sqlalchemy.engine import make_url

_SECURE_SSL_VALUES = {"1", "true", "require", "verify-ca", "verify-full"}
_DISABLED_SSL_VALUES = {"0", "false", "disable"}


def prepare_asyncpg_connection(database_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize common managed-Postgres URLs for SQLAlchemy's asyncpg dialect.

    Providers such as Neon commonly issue ``postgresql://`` URLs with libpq-style
    query parameters (for example ``sslmode=require`` and ``channel_binding=require``).
    The application uses SQLAlchemy's asyncpg dialect, so the driver name and TLS
    arguments need to be adapted without weakening transport security.
    """

    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    elif url.drivername != "postgresql+asyncpg":
        return database_url, {}

    query: dict[str, Any] = dict(url.query)
    ssl_value = _pop_query_value(query, "sslmode")
    explicit_ssl = _pop_query_value(query, "ssl")
    _pop_query_value(query, "channel_binding")

    if ssl_value is None:
        ssl_value = explicit_ssl

    connect_args: dict[str, Any] = {}
    if ssl_value is not None:
        normalized = ssl_value.casefold()
        if normalized in _SECURE_SSL_VALUES:
            connect_args["ssl"] = True
        elif normalized in _DISABLED_SSL_VALUES:
            connect_args["ssl"] = False
        else:
            raise ValueError(f"Unsupported PostgreSQL SSL mode for asyncpg: {ssl_value}")

    normalized_url = url.set(query=query)
    return normalized_url.render_as_string(hide_password=False), connect_args


def _pop_query_value(
    query: dict[str, Any], key: str
) -> str | None:
    value = query.pop(key, None)
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        return str(value[-1]) if value else None
    return str(value)
