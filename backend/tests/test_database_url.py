import pytest

from backend import db as database


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_managed_postgres_urls_keep_ssl_and_credentials(monkeypatch, scheme):
    monkeypatch.setenv("DATABASE_URL", f"{scheme}://demo:p%40ss@example.neon.tech/demo?sslmode=require")
    captured = {}

    def create_engine(url, **options):
        captured.update(url=url, options=options)
        return "engine"

    monkeypatch.setattr(database, "create_engine", create_engine)
    assert database.create_database_engine() == "engine"
    assert captured["url"].drivername == "postgresql+psycopg"
    assert captured["url"].password == "p@ss"
    assert captured["url"].query["sslmode"] == "require"
    assert captured["options"]["connect_args"]["connect_timeout"] == 5


@pytest.mark.parametrize("value", ["", "sqlite:///demo.db", "mysql://demo:secret@example.com/demo"])
def test_non_postgres_or_missing_url_is_rejected(monkeypatch, value):
    monkeypatch.setenv("DATABASE_URL", value)
    with pytest.raises(RuntimeError):
        database.create_database_engine()
