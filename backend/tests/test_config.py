from app.core.config import Settings


def test_cors_origins_parses_csv() -> None:
    settings = Settings(cors_origins="http://localhost:3000,https://example.test")
    assert settings.cors_origins == ["http://localhost:3000", "https://example.test"]


def test_trusted_hosts_parses_csv() -> None:
    settings = Settings(trusted_hosts="localhost,backend,example.test")
    assert settings.trusted_hosts == ["localhost", "backend", "example.test"]
