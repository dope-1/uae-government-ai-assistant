from app.db.connection import prepare_asyncpg_connection


def test_prepare_asyncpg_connection_keeps_local_url_unchanged() -> None:
    url, connect_args = prepare_asyncpg_connection(
        "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    assert url == "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert connect_args == {}


def test_prepare_asyncpg_connection_adapts_neon_style_url() -> None:
    url, connect_args = prepare_asyncpg_connection(
        "postgresql://user:pass@example.neon.tech/db"
        "?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+asyncpg://user:pass@example.neon.tech/db"
    assert connect_args == {"ssl": True}


def test_prepare_asyncpg_connection_preserves_non_ssl_query_parameters() -> None:
    url, connect_args = prepare_asyncpg_connection(
        "postgresql://user:pass@example.neon.tech/db"
        "?sslmode=require&prepared_statement_cache_size=0"
    )
    assert "prepared_statement_cache_size=0" in url
    assert connect_args == {"ssl": True}


def test_prepare_asyncpg_connection_rejects_unknown_ssl_mode() -> None:
    try:
        prepare_asyncpg_connection(
            "postgresql://user:pass@example.neon.tech/db?sslmode=mystery"
        )
    except ValueError as exc:
        assert "Unsupported PostgreSQL SSL mode" in str(exc)
    else:
        raise AssertionError("Expected unsupported SSL mode to be rejected")
