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
    
    # DRT Ping Schedule Configuration
    drt_stop_detection_radius_m: int = 500
    drt_surge_ping_threshold: int = 50
    drt_clustering_interval_minutes: int = 5
    drt_ping_expiry_minutes: int = 30
    
    # DRT Phase 2 Configuration
    drt_clustering_enabled: bool = True
    drt_next_bus_gap_minutes: int = 15
    drt_websocket_enabled: bool = True
    drt_websocket_max_connections: int = 50
    
    # DRT Phase 3: Ghost Bus Suppression Configuration
    ghost_bus_threshold: int = 5
    ghost_bus_analysis_days: int = 30
    ghost_bus_min_occurrences: int = 3
    ghost_bus_auto_approve: bool = False
    ghost_bus_analysis_time: str = "02:00"
    
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
