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
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_socket_timeout: float = Field(default=5.0, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: float = Field(default=5.0, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_decode_responses: bool = Field(default=True, alias="REDIS_DECODE_RESPONSES")
    redis_health_check_interval: int = Field(default=30, alias="REDIS_HEALTH_CHECK_INTERVAL")
    
    # Cache Configuration
    cache_default_ttl: int = Field(default=3600, alias="CACHE_DEFAULT_TTL")  # 1 hour default
    cache_key_prefix: str = Field(default="rtac_modbus", alias="CACHE_KEY_PREFIX")
    
    # Database Configuration
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="rtac_modbus", alias="POSTGRES_DB")
    postgres_user: str = Field(default="rtac_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="rtac_password", alias="POSTGRES_PASSWORD")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Scheduler Configuration
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_leader_lock_ttl: int = Field(default=30, alias="SCHEDULER_LEADER_LOCK_TTL")
    scheduler_heartbeat_interval: int = Field(default=10, alias="SCHEDULER_HEARTBEAT_INTERVAL")
    scheduler_job_lock_ttl: int = Field(default=300, alias="SCHEDULER_JOB_LOCK_TTL")
    scheduler_leader_retry_interval: int = Field(default=5, alias="SCHEDULER_LEADER_RETRY_INTERVAL")
    
    # Polling Job Configuration
    poll_interval_seconds: int = Field(default=60, alias="POLL_INTERVAL_SECONDS")
    poll_register_map_path: str = Field(default="config/sel_751_register_map.csv", alias="POLL_REGISTER_MAP_PATH")
    poll_cache_ttl: int = Field(default=3600, alias="POLL_CACHE_TTL")  # 1 hour default
    
    main_sel_751_poll_address: int = Field(default=1400, alias="MAIN_SEL_751_POLL_ADDRESS")  # Fixed Modbus address to read from
    main_sel_751_poll_count: int = Field(default=100, alias="MAIN_SEL_751_POLL_COUNT")  # Fixed number of registers to read
    main_sel_751_poll_kind: str = Field(default="holding", alias="MAIN_SEL_751_POLL_KIND")  # Register type: holding, input, coils, discretes
    main_sel_751_poll_unit_id: int = Field(default=1, alias="MAIN_SEL_751_POLL_UNIT_ID")  # Modbus unit ID
    
    # Pod identification (for Kubernetes)
    pod_name: str = Field(default="", alias="POD_NAME")  # Falls back to HOSTNAME if not set
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

