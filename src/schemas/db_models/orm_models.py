"""
SQLAlchemy ORM models for database tables.

These models represent the database schema and are used for ORM operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from sqlalchemy import String, Integer, Text, DateTime, func, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class Device(Base):
    """
    SQLAlchemy model for the devices table.
    
    Represents a Modbus device configuration.
    """
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(
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
        comment="Modbus device hostname or IP address"
    )
    
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=502,
        comment="Modbus TCP port (default: 502)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
        index=True,
        default=1,
        comment="Modbus unit/slave ID (unique)"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional device description"
    )
    
    # Polling configuration
    poll_address: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Start address for polling Modbus registers"
    )
    
    poll_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of registers to read during polling"
    )
    
    poll_kind: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="holding",
        comment="Register type: holding, input, coils, or discretes"
    )
    
    poll_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether polling is enabled for this device"
    )
    
    # Foreign key to Site
    site_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Foreign key to sites table (optional - device can exist without a site)"
    )
    
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
    
    # Relationship to RegisterReading
    register_readings: Mapped[list["RegisterReading"]] = relationship(
        "RegisterReading",
        back_populates="device",
        cascade="all, delete-orphan"
    )
    
    # Relationship to DeviceRegisterMap (one-to-one)
    register_map: Mapped[Optional["DeviceRegisterMap"]] = relationship(
        "DeviceRegisterMap",
        back_populates="device",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Relationship to Site (many-to-one)
    site: Mapped[Optional["Site"]] = relationship(
        "Site",
        back_populates="devices"
    )
    
    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name='{self.name}', host='{self.host}:{self.port}')>"


class RegisterReading(Base):
    """
    SQLAlchemy model for the register_readings table.
    
    Represents a time-series data point for a Modbus register reading.
    Uses composite primary key (timestamp, device_id, register_address).
    """
    __tablename__ = "register_readings"
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        comment="Timestamp when the reading was taken (UTC)"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
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
        return f"<RegisterReading(timestamp={self.timestamp}, device_id={self.device_id}, register_address={self.register_address}, value={self.value})>"


class DeviceRegisterMap(Base):
    """
    SQLAlchemy model for the device_register_map table.
    
    Represents a device register map configuration stored as JSONB.
    One-to-one relationship with Device.
    """
    __tablename__ = "device_register_map"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key, auto-incrementing"
    )
    
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="Foreign key to devices table (one-to-one relationship)"
    )
    
    register_map: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Device register map configuration stored as JSONB"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when register map was created"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when register map was last updated"
    )
    
    # Relationship to Device
    device: Mapped["Device"] = relationship("Device", back_populates="register_map")
    
    def __repr__(self) -> str:
        return f"<DeviceRegisterMap(id={self.id}, device_id={self.device_id})>"


class Site(Base):
    """
    SQLAlchemy model for the sites table.
    
    Represents a site/location where devices are deployed.
    """
    __tablename__ = "sites"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key, UUID string"
    )
    
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Site owner"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Site name (must be unique)"
    )
    
    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Site location"
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
    
    # Relationship to Device (one-to-many)
    devices: Mapped[list["Device"]] = relationship(
        "Device",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name='{self.name}', location='{self.location}')>"

