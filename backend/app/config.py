from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "FormFix"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database: SQLite default for zero-friction execution, swappable to PostgreSQL
    DATABASE_URL: str = "sqlite:///./formfix.db"
    
    # Security & Encryption
    SECRET_KEY: str = "dev-secret-key-formfix-hackathon-2026-secure"
    STORAGE_ENCRYPTION_KEY: str = "ZXZwM0ptVlJBNlZlQmI4RkZ3N3N1c0pqa3Z6N3R1c0k="  # Fernet AES-128 key for encryption-at-rest
    SESSION_EXPIRE_MINUTES: int = 30
    
    # DPDP Act 2023 Consent Policy
    CONSENT_POLICY_VERSION: str = "v2.0-dpdp-formfix-2026"
    
    # Storage
    TEMP_STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_uploads")
    
    # Demo / Test Mode Flag
    DEMO_MODE_ENABLED: bool = True
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
