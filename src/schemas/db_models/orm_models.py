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


class RegisterConfig(TypedDict, total=False):
    register_address: int
    register_name: str
    data_type: str
    size: int
    scale_factor: float
    unit: str
    bitfield_detail: Dict[str, str]
    enum_detail: Dict[str, str]


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
    
    # configs moved to device_configs table
    
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


class DeviceConfig(Base):
    """
    SQLAlchemy model for the device_configs table.
    
    Stores device configuration payloads keyed by a config ID string.
    """
    __tablename__ = "device_configs"
    
    id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="Device config ID (e.g., siteID-deviceID-1)"
    )
    
    site_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Site ID (4-digit number)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Device ID (database primary key)"
    )
    
    poll_address: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Start address for polling Modbus registers"
    )
    
    poll_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of registers to read during polling"
    )
    
    poll_kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Register type: holding, input, coils, or discretes"
    )
    
    registers: Mapped[list[RegisterConfig]] = mapped_column(
        JSON,
        nullable=False,
        comment="Register definitions"
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
        return f"<DeviceConfig(id='{self.id}')>"


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
