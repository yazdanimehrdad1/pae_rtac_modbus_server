"""
Application configuration using Pydantic Settings.

Environment-driven configuration with validation and type safety.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Modbus Configuration
    modbus_host: str = Field(default="localhost", alias="MODBUS_HOST")
    modbus_port: int = Field(default=502, alias="MODBUS_PORT")
    modbus_unit_id: int = Field(default=1, alias="MODBUS_UNIT_ID")
    modbus_timeout_s: float = Field(default=5.0, alias="MODBUS_TIMEOUT_S")
    modbus_retries: int = Field(default=3, alias="MODBUS_RETRIES")
    
    # Server Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Database Configuration (TODO: Add when implementing TimescaleDB)
    # database_url: str = Field(..., alias="DATABASE_URL")
    # database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    # database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    
    # Scheduler Configuration (TODO: Add when implementing polling)
    # poll_interval_seconds: int = Field(default=60, alias="POLL_INTERVAL_SECONDS")
    # poll_jitter_seconds: int = Field(default=5, alias="POLL_JITTER_SECONDS")
    # max_concurrent_polls: int = Field(default=10, alias="MAX_CONCURRENT_POLLS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

