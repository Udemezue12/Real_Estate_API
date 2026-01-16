import os
from datetime import datetime, timedelta, timezone
from typing import ClassVar, List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from .url_parser import parser

load_dotenv()


class Settings(BaseSettings):
    FLUTTERWAVE_BASE_URL: str = "https://api.flutterwave.com/v3"
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    REDIRECT_URL: str | None = os.getenv("REDIRECT_URL")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    RENDER_DATABASE_URL: str | None = os.getenv("RENDER_DATABASE_URL")
    PROJECT_NAME: str = "REAL ESTATE MANAGEMENT And SALES SYSTEM"
    RATE_LIMIT_REDIS_URL: str = (
        f"redis://{os.getenv('RATE_LIMIT_REDIS_USERNAME')}:{os.getenv('RATE_LIMIT_REDIS_PASSWORD')}"
        f"@{os.getenv('RATE_LIMIT_REDIS_HOST')}:{os.getenv('RATE_LIMIT_REDIS_PORT')}/0"
    )
    CELERY_REDIS_URL: str = (
        f"rediss://{os.getenv('CELERY_REDIS_USERNAME')}:{os.getenv('CELERY_REDIS_PASSWORD')}"
        f"@{os.getenv('CELERY_REDIS_HOST')}:{os.getenv('CELERY_REDIS_PORT')}/0"
    )
    RABBITMQ_MAIN_EXCHANGE: str = "location_events"
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "")
    RABBITMQ_DLX: str = "dead_letter_exchange"
    RABBITMQ_DLX_QUEUE: str = "dead_letter_queue"
    REDIS_URL: str = os.getenv(
        "REDIS_URL", "rediss://:123456789@gusc1-related-narwhal-32244.upstash.io:6379"
    )
    GEOAPIFY_API_KEY: str | None = os.getenv("GEOAPIFY_API_KEY")
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    RATE_LIMIT: str = "20/minute"
    UPSTASH_REDIS_TOKEN: str | None = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    UPSTASH_REDIS_URL: str | None = os.getenv("UPSTASH_REDIS_REST_URL")
    EMAIL_USER: str | None = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
    EMAIL_SERVER: str | None = os.getenv("EMAIL_SERVER")
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    RESET_SECRET_KEY: str | None = os.getenv("RESET_SECRET_KEY")
    VERIFY_EMAIL_SECRET_KEY: str | None = os.getenv("VERIFY_EMAIL_SECRET_KEY")
    RESET_PASSWORD_SALT: str = "password-reset-salt"
    VERIFY_EMAIL_SALT: str = "verify-reset-salt"
    FRONTEND_URL: str | None = os.getenv("FRONTEND_URL")
    JWT_SECRET_KEY: str | None = os.getenv("JWT_SECRET_KEY")
    ALGORITHM: str | None = os.getenv("ALGORITHM")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    RP_ID: str | None = os.getenv("DEV_RP_ID")
    WEBAUTHN_ORIGIN: str  = "http://localhost:8000"
    ORIGIN: str | None = os.getenv("DEV_ORIGIN")
    SECURE: str | None = os.getenv("secure")
    TERMII_API_KEY: str | None = os.getenv("TERMII_API_KEY")
    CLOUDINARY_CLOUD_NAME: str | None = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str | None = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_SECRET_KEY: str | None = os.getenv("CLOUDINARY_SECRET_KEY")
    TERMII_SENDER_ID: str | None = os.getenv("TERMII_SENDER_ID")
    TERMII_BASE_URL: str | None = os.getenv("TERMII_BASE_URL")
    ACCESS_EXPIRE_MINUTES: int = 10
    REFRESH_EXPIRE_DAYS: int = 5
    CSRF_TOKEN_EXPIRE_DAYS: int = 5
    SECURE_COOKIES: bool = False  # must be false on localhost
    SECRET_KEY: str | None = os.getenv("SECRET_KEY")
    jwt_expiration: ClassVar[datetime] = datetime.now(timezone.utc) + timedelta(hours=1)
    access_key_jwt_expiration: ClassVar[datetime] = datetime.now(
        timezone.utc
    ) + timedelta(minutes=10)
    refresh_expiration_jwt_expiration: ClassVar[datetime] = datetime.now(
        timezone.utc
    ) + timedelta(days=5)

    MAX_RESENDS: int = 3
    LOCK_DURATION: ClassVar[timedelta] = timedelta(hours=2)
    csrf_token_expiration: ClassVar[datetime] = datetime.now(timezone.utc) + timedelta(
        days=5
    )
    CRITICAL_SERVICE_RAW: str = os.getenv("CRITICAL_SERVICE_URLS", "")
    RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY")
    RESEND_SENDER: str | None = os.getenv("RESEND_SENDER")
    FLUTTERWAVE_SECRET_KEY: str | None = os.getenv("FLUTTERWAVE_SECRET_KEY")
    PAYSTACK_SECRET_KEY: str | None = os.getenv("PAYSTACK_SECRET_KEY")
    ADMIN_REDIS_URL: str | None = os.getenv("ADMIN_REDIS_URL")
    ALLOWED_HOSTS_RAW: str = os.getenv("ALLOWED_HOSTS", "")

    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        return parser.parse_url_list(self.ALLOWED_HOSTS_RAW, "ALLOWED_HOSTS")

    @property
    def CRITICAL_SERVICE_URLS(self) -> List[str]:
        return parser.parse_url_list(
            self.CRITICAL_SERVICE_RAW,
            "CRITICAL_SERVICE_URLS",
        )

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


settings = Settings()
