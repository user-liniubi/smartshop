from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    app_name: str = Field(default="SmartShop AI", min_length=1)
    app_env: Environment = "development"
    debug: bool = False
    log_level: LogLevel = "INFO"
    database_url: str = Field(
        default="mysql+pymysql://smartshop:replace_me@127.0.0.1:3306/smartshop",
        min_length=1,
    )
    database_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env == "production" and "replace_me" in self.database_url:
            raise ValueError("生产环境必须配置真实的 DATABASE_URL")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide settings instance."""

    return Settings()
