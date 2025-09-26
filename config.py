import os
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str = "mongodb+srv://parkproplus_db_user:vacation@vacation-planner.tvg1alp.mongodb.net/?retryWrites=true&w=majority&appName=vacation-planner"
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Security settings
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000","http://localhost:8080"]

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if v is None or v == "":
            return cls.cors_origins  # Use default
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            # Try parsing as JSON first
            try:
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if origin]
            except (json.JSONDecodeError, ImportError):
                pass
            # Fallback to comma-separated
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

    # Logging settings
    log_level: str = "INFO"
    enable_structured_logging: bool = True

    # Export settings
    enable_pdf_export: bool = True
    enable_calendar_export: bool = True

    # OAuth settings
    google_client_id: str = ""
    google_client_secret: str = ""
    apple_client_id: str = ""
    apple_client_secret: str = ""

    # Email settings for password reset
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@travelmate.com"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001

    class Config:
        env_file = ".env"

settings = Settings()

