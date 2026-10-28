import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "SmartShop Test")
    monkeypatch.setenv("APP_ENV", "TEST")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.app_name == "SmartShop Test"
    assert settings.app_env == "test"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"


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
