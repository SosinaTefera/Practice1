import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Project Information
    PROJECT_NAME: str = "Nexia Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./nexia.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    ALGORITHM: str = "HS256"
    PASSWORD_RESET_EXPIRE_MINUTES: int = int(
        os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "15")
    )
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = int(
        os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24")
    )

    # SMTP / Email
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_SENDER: Optional[str] = os.getenv("SMTP_SENDER")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # Mailjet (preferred email service)
    MAILJET_API_KEY: Optional[str] = os.getenv("MAILJET_API_KEY")
    MAILJET_SECRET_KEY: Optional[str] = os.getenv("MAILJET_SECRET_KEY")
    MAILJET_SENDER: Optional[str] = os.getenv("MAILJET_SENDER")
    MAILJET_SENDER_NAME: Optional[str] = os.getenv("MAILJET_SENDER_NAME", "Nexia Fitness")

    # Frontend URLs
    # Base URL used to compose password reset links in emails
    FRONTEND_RESET_URL: str = os.getenv(
        "FRONTEND_RESET_URL", "https://nexia-frontend-phi.vercel.app/reset-password"
    )
    # Base URL used to compose email verification links in emails
    FRONTEND_VERIFICATION_URL: str = os.getenv(
        "FRONTEND_VERIFICATION_URL", "https://nexia-frontend-phi.vercel.app/verify-email"
    )

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Allowed hosts for TrustedHostMiddleware (hostnames only, no scheme)
    ALLOWED_HOSTS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # File Upload
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")

    # Pagination
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
