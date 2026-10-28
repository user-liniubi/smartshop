import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "SmartShop Test")
    monkeypatch.setenv("APP_ENV", "TEST")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://smartshop:test_password@127.0.0.1:3308/smartshop",
    )
    monkeypatch.setenv("DATABASE_ECHO", "true")
    monkeypatch.setenv("AUTH_SECRET", "test-secret-with-at-least-32-characters")
    monkeypatch.setenv("AUTH_TOKEN_EXPIRE_MINUTES", "15")

    settings = Settings(_env_file=None)

    assert settings.app_name == "SmartShop Test"
    assert settings.app_env == "test"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.database_url.endswith("/smartshop")
    assert settings.database_echo is True
    assert settings.auth_secret == "test-secret-with-at-least-32-characters"
    assert settings.auth_token_expire_minutes == 15


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("APP_ENV", "staging"),
        ("LOG_LEVEL", "verbose"),
        ("APP_NAME", ""),
    ],
)
def test_invalid_settings_are_rejected(monkeypatch, field, value):
    monkeypatch.setenv(field, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
