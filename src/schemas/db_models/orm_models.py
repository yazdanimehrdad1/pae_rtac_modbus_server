"""
SQLAlchemy ORM models for database tables.

These models represent the database schema and are used for ORM operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, TypedDict
from sqlalchemy import String, Integer, Text, DateTime, func, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class ConfigPointDefinition(TypedDict, total=False):
    point_address: int
    point_name: str
    point_data_type: str
    point_size: int
    point_scale_factor: float
    point_unit: str
    point_bitfield_detail: Dict[str, str]
    point_enum_detail: Dict[str, str]


class Site(Base):
    """
    SQLAlchemy model for the sites table.
    
    Represents a site/location where devices are deployed.
    """
    __tablename__ = "sites"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Primary key, 4-digit site ID"
    )
    
    client_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Client identifier"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Site name (must be unique)"
    )
    
    location: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Site location as JSON: {street: str, city: str, zip_code: int}"
    )
    
    operator: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Site operator"
    )
    
    capacity: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Site capacity"
    )
    
    device_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of devices at this site (denormalized for performance)"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional site description"
    )
    
    coordinates: Mapped[Optional[Dict[str, float]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Geographic coordinates as JSON: {lat: float, lng: float}"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when site record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when site record was last updated"
    )
    
    last_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp of last update (synced from external source)"
    )
    
    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name='{self.name}', location='{self.location}')>"


class Device(Base):
    """
    SQLAlchemy model for the devices table.
    
    Represents a Modbus device configuration.
    """
    __tablename__ = "devices"
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key, auto-incrementing"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique device name/identifier"
    )
    
    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Device hostname or IP address"
    )
    
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=502,
        comment="Device port (default: 502)"
    )
    
    timeout: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Optional timeout (seconds)"
    )
    
    site_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Site ID (required)"
    )
    
    server_address: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Server address"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional device description"
    )
    
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Device type"
    )
    
    vendor: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Device vendor"
    )
    
    model: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Device model"
    )
    
    # Polling configuration
    poll_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether polling is enabled for this device"
    )

    read_from_aggregator: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this device reads data from the edge aggregator"
    )
    
    # configs stored in configs table
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when device record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when device record was last updated"
    )
    
    # Relationship to RegisterReadingRaw
    register_readings: Mapped[list["RegisterReadingRaw"]] = relationship(
        "RegisterReadingRaw",
        back_populates="device",
        cascade="all, delete-orphan"
    )

    # Relationship to RegisterReadingTranslated
    register_readings_translated: Mapped[list["RegisterReadingTranslated"]] = relationship(
        "RegisterReadingTranslated",
        back_populates="device",
        cascade="all, delete-orphan"
    )
    
    
    
    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id}, name='{self.name}', host='{self.host}:{self.port}')>"


class Config(Base):
    """
    SQLAlchemy model for the configs table.
    
    Stores versioned polling configuration payloads keyed by config ID.
    """
    __tablename__ = "configs"
    
    config_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Config ID (e.g., siteID-deviceID-1)"
    )
    
    site_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Site ID (4-digit number)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        comment="Device ID (database primary key)"
    )
    
    poll_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Register type: holding, input, or coils"
    )
    
    poll_start_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Start index for polling Modbus registers"
    )
    
    poll_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of registers to read during polling"
    )
    
    points: Mapped[list[ConfigPointDefinition]] = mapped_column(
        JSON,
        nullable=False,
        comment="Point definitions"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this config is active"
    )
    
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Config creator identifier"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when config record was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when config record was last updated"
    )
    
    def __repr__(self) -> str:
        return f"<Config(config_id='{self.config_id}')>"


class RegisterReadingRaw(Base):
    """
    SQLAlchemy model for the register_readings_raw table.
    
    Represents a time-series data point for a Modbus register reading.
    Uses composite primary key (timestamp, device_id, register_address).
    """
    __tablename__ = "register_readings_raw"
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        comment="Timestamp when the reading was taken (UTC)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="Foreign key to devices table"
    )
    
    register_address: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Modbus register address"
    )
    
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="The actual register value"
    )
    
    quality: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default='good',
        comment="Data quality flag: good, bad, uncertain, or substituted"
    )
    
    register_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Register name (denormalized from register_map for performance)"
    )
    
    unit: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Unit of measurement (denormalized from register_map)"
    )
    
    scale_factor: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Scale factor to apply to raw value (denormalized from register_map)"
    )
    
    # Relationship to Device
    device: Mapped["Device"] = relationship("Device", back_populates="register_readings")
    
    def __repr__(self) -> str:
        return f"<RegisterReadingRaw(timestamp={self.timestamp}, device_id={self.device_id}, register_address={self.register_address}, value={self.value})>"


class RegisterReadingTranslated(Base):
    """
    SQLAlchemy model for the register_readings_translated table.
    
    Represents a time-series data point for a translated Modbus register reading.
    Uses composite primary key (timestamp, device_id, register_address).
    """
    __tablename__ = "register_readings_translated"
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        comment="Timestamp when the reading was taken (UTC)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        comment="Foreign key to devices table"
    )
    
    register_address: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Modbus register address"
    )
    
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="The actual register value"
    )
    
    quality: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default='good',
        comment="Data quality flag: good, bad, uncertain, or substituted"
    )
    
    register_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Register name (denormalized from register_map for performance)"
    )
    
    unit: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Unit of measurement (denormalized from register_map)"
    )
    
    scale_factor: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Scale factor to apply to raw value (denormalized from register_map)"
    )

    value_scaled: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="The scaled register value"
    )

    enum_detail: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Enum detail mapping (denormalized from register_map)"
    )

    bitfield_detail: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Bitfield detail mapping (denormalized from register_map)"
    )

    # Relationship to Device
    device: Mapped["Device"] = relationship("Device", back_populates="register_readings_translated")
    
    def __repr__(self) -> str:
        return (
            f"<RegisterReadingTranslated(timestamp={self.timestamp}, device_id={self.device_id}, "
            f"register_address={self.register_address}, value={self.value})>"
        )


class DevicePoint(Base):
    """
    SQLAlchemy model for the device_points table.
    
    Represents a flattened point definition for a device.
    """
    __tablename__ = "device_points"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key"
    )
    
    site_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Site ID"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Device ID"
    )
    
    config_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("configs.config_id", ondelete="CASCADE"),
        nullable=False,
        comment="Config ID"
    )
    
    address: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Point address"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Point name (must be unique per device)"
    )
    
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Point size"
    )
    
    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Data type"
    )
    
    scale_factor: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Scale factor"
    )
    
    unit: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit"
    )
    
    enum_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Enum value if applicable"
    )
    
    bitfield_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bitfield value if applicable"
    )

    # Note: Unique constraint on (device_id, name) is enforced logic-side or via separate constraint
    # We avoid strict DB constraint here to allow logic-side custom error handling as requested,
    # OR we can add it. User asked to check manually.
    
    def __repr__(self) -> str:
        return f"<DevicePoint(id={self.id}, name='{self.name}', device_id={self.device_id})>"

