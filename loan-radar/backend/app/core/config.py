from functools import lru_cache
from pathlib import Path
from typing import List
import secrets as _secrets
import sys

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

_DEV_SECRET_KEY = "dev-only-change-me-in-production-32ch"


class Settings(BaseSettings):
    app_name: str = Field(default="Loan Radar Backend", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    database_url: str = Field(
        default="postgresql+psycopg2://loan_radar:loan_radar_password@localhost:5432/loan_radar",
        alias="DATABASE_URL",
    )

    secret_key: str = Field(default=_DEV_SECRET_KEY, alias="SECRET_KEY")
    fernet_key: str = Field(default="", alias="FERNET_KEY")

    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_interval_seconds: int = Field(default=60, alias="SCHEDULER_INTERVAL_SECONDS")

    asset_storage_type: str = Field(default="local", alias="ASSET_STORAGE_TYPE")

    frontend_serve_static: bool = Field(default=False, alias="FRONTEND_SERVE_STATIC")
    frontend_build_dir: str = Field(default="./frontend/dist", alias="FRONTEND_BUILD_DIR")

    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:8001,http://localhost:8001",
        alias="CORS_ORIGINS",
    )

    media_crawler_api_url: str = Field(default="http://127.0.0.1:8080", alias="MEDIA_CRAWLER_API_URL")
    media_crawler_timeout: int = Field(default=300, alias="MEDIA_CRAWLER_TIMEOUT")
    media_crawler_home: str = Field(default="", alias="MEDIA_CRAWLER_HOME")
    media_crawler_raw_db_path: str = Field(default="", alias="MEDIA_CRAWLER_RAW_DB_PATH")
    media_crawler_cookies: str = Field(default="", alias="MEDIA_CRAWLER_COOKIES")

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_dir(self) -> Path:
        return Path(BASE_DIR) / "storage"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.secret_key or s.secret_key == _DEV_SECRET_KEY:
        if s.is_production:
            s.secret_key = _secrets.token_urlsafe(48)
            print(
                "[WARN] SECRET_KEY not set in production — auto-generated. "
                "Tokens will invalidate on restart. Set SECRET_KEY env var for stability.",
                file=sys.stderr,
            )
        else:
            print(
                "[WARN] Using default SECRET_KEY — only acceptable in development.",
                file=sys.stderr,
            )
    return s


settings = get_settings()
