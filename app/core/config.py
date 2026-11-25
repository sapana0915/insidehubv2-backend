from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


Environment = Literal["dev", "prod", "test"]

CONFIG: Dict[str, Dict[str, Any]] = {
    "dev": {
        "DEBUG": True,
        "SECRET_KEY": "dev-secret-key-change-in-production",
        "DATABASE_URL": "postgresql://postgres:pgadmin12345@db:5432/insidehubv2_db",
        "REDIS_URL": "redis://redis:6379/0",
        "CELERY_BROKER_URL": "amqp://guest:guest@rabbitmq:5672//",
        "CELERY_RESULT_BACKEND_URL": "redis://redis:6379/0",
        "CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000",
    },
    "prod": {
        "DEBUG": False,
        "SECRET_KEY": "",
        "DATABASE_URL": "",
        "REDIS_URL": "redis://redis:6379/0",
        "CELERY_BROKER_URL": "amqp://guest:guest@rabbitmq:5672//",
        "CELERY_RESULT_BACKEND_URL": "redis://redis:6379/0",
        "CORS_ORIGINS": "",
    },
    "test": {
        "DEBUG": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE_URL": "sqlite:///./test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "CELERY_BROKER_URL": "memory://",
        "CELERY_RESULT_BACKEND_URL": "cache+memory://",
        "CORS_ORIGINS": "*",
    },
}


def _env_block() -> Dict[str, Any]:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    if env not in CONFIG:
        env = "dev"
    return CONFIG[env]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    ENVIRONMENT: Environment = "dev"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = "postgresql://postgres:pgadmin12345@db:5432/insidehubv2_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    MEDIA_DIR: str = "media"
    MEDIA_URL: str = "/media"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    # "local" saves files under MEDIA_DIR. "s3" is for later, after local uploads work.
    STORAGE_BACKEND: Literal["local", "s3"] = "local"

    # WebP quality is 1–100. 80 is sharp enough for photos and much smaller than the original.
    WEBP_QUALITY: int = 80

    # Width × height after decompression. Stops a small file from expanding into a huge image.
    MAX_IMAGE_PIXELS: int = 20_000_000

    # Pillow's names. JPEG, not JPG.
    ALLOWED_IMAGE_FORMATS: str = "JPEG,PNG,WEBP,GIF"

    PROFILE_IMAGE_SIZE: int = 400
    POST_THUMBNAIL_WIDTH: int = 400
    POST_THUMBNAIL_HEIGHT: int = 300
    POST_COVER_WIDTH: int = 1920
    POST_COVER_HEIGHT: int = 1080
    POST_CONTENT_MAX_WIDTH: int = 1600
    POST_CONTENT_MAX_HEIGHT: int = 1200

    # Used only when STORAGE_BACKEND=s3. Leave blank while testing locally.
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_PUBLIC_BASE_URL: str = ""
    AWS_S3_ENDPOINT_URL: str = ""

    # "console" prints the code in the logs; "smtp" sends a real email.
    EMAIL_BACKEND: Literal["console", "smtp"] = "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "InsideHub <no-reply@insidehub.local>"

    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_RESEND_COOLDOWN_SECONDS: int = 60

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""
    AI_MODEL: str = "gpt-oss-20b"
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_OUTPUT_TOKENS: int = 2000
    AI_DRAFTS_PER_DAY: int = 3
    # Every model call, including follow-up questions; stops the free questions step being abused.
    AI_CALLS_PER_DAY: int = 30
    # "News event" drafts that search the web. Only providers with a built-in browser_search tool (Groq gpt-oss).
    AI_WEB_SEARCH_ENABLED: bool = False
    AI_SEARCH_MODEL: str = ""
    AI_SEARCH_TIMEOUT_SECONDS: float = 90.0
    AI_WEB_SEARCH_CATEGORIES: str = "tech"

    @property
    def web_search_categories(self) -> set[str]:
        return {slug.strip().lower() for slug in self.AI_WEB_SEARCH_CATEGORIES.split(",") if slug.strip()}

    @property
    def allowed_image_formats(self) -> set[str]:
        return {
            item.strip().upper()
            for item in self.ALLOWED_IMAGE_FORMATS.split(",")
            if item.strip()
        }

    def __init__(self, **kwargs: Any) -> None:
        block = _env_block()
        merged: Dict[str, Any] = {}
        for key in (
            "DEBUG",
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND_URL",
            "CORS_ORIGINS",
        ):
            if key not in kwargs and key in block and block[key] not in ("", None):
                merged[key] = block[key]
        merged.update(kwargs)
        super().__init__(**merged)
        self._validate_production()
        self._validate_storage()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @field_validator("WEBP_QUALITY")
    @classmethod
    def check_webp_quality(cls, value: int) -> int:
        if not 1 <= value <= 100:
            raise ValueError("WEBP_QUALITY must be between 1 and 100")
        return value

    def _validate_production(self) -> None:
        if self.ENVIRONMENT != "prod":
            return
        if not self.SECRET_KEY or self.SECRET_KEY == CONFIG["dev"]["SECRET_KEY"]:
            raise ValueError("SECRET_KEY must be set to a strong value in production")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL must be set in production")

    def _validate_storage(self) -> None:
        if self.STORAGE_BACKEND != "s3":
            return
        missing = [
            name
            for name, value in (
                ("AWS_S3_BUCKET", self.AWS_S3_BUCKET),
                ("AWS_S3_REGION", self.AWS_S3_REGION),
            )
            if not str(value).strip()
        ]
        if missing:
            raise ValueError("STORAGE_BACKEND=s3 requires " + ", ".join(missing))


settings = Settings(ENVIRONMENT=os.getenv("ENVIRONMENT", "dev"))  # type: ignore[arg-type]
