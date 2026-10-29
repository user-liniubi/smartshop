from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    auth_secret: str = Field(
        default="dev-only-change-this-secret-32chars",
        min_length=32,
    )
    auth_token_expire_minutes: int = Field(default=60, ge=1, le=1440)
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: int = Field(default=30, ge=1, le=120)
    chroma_path: Path = Path("./data/chroma")
    upload_dir: Path = Path("./data/uploads")
    knowledge_docs_dir: Path = Path("./data/docs")
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: Literal["cpu", "cuda"] = "cpu"
    embedding_local_files_only: bool = False
    rag_chunk_size: int = Field(default=500, ge=100, le=2000)
    rag_chunk_overlap: int = Field(default=80, ge=0, le=500)
    rag_top_k: int = Field(default=4, ge=1, le=10)
    rag_min_similarity: float = Field(default=0.5, ge=-1, le=1)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)

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

    @field_validator("deepseek_api_key", mode="before")
    @classmethod
    def normalize_deepseek_key(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, SecretStr):
            raw_value = value.get_secret_value()
        elif isinstance(value, str):
            raw_value = value
        else:
            return value

        stripped_value = raw_value.strip()
        if not stripped_value or stripped_value == "replace_me":
            return None
        return stripped_value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env == "production" and "replace_me" in self.database_url:
            raise ValueError("生产环境必须配置真实的 DATABASE_URL")
        if self.app_env == "production" and self.auth_secret.startswith("dev-only"):
            raise ValueError("生产环境必须替换 AUTH_SECRET")
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP 必须小于 RAG_CHUNK_SIZE")
        if self.app_env == "production" and self.deepseek_api_key is None:
            raise ValueError("生产环境必须配置 DEEPSEEK_API_KEY")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide settings instance."""

    return Settings()
