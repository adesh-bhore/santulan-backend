"""Application Configuration

Manages environment variables and application settings using Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    database_url: str = "postgresql://pmpml_user:pmpml_password@localhost:5432/pmpml_optimization"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # CORS Configuration
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    
    # Optimization Configuration
    solver_time_limit_sec: int = 120
    default_max_duty_min: int = 480
    
    # Celery Configuration (Optional)
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # JWT Authentication Configuration
    jwt_secret_key: str = "your-secret-key-change-this-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 24
    jwt_refresh_token_expire_days: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
