"""
SQLAlchemy ORM models for database tables.

These models represent the database schema and are used for ORM operations.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    
    unit_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Modbus unit/slave ID"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional device description"
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
    
    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name='{self.name}', host='{self.host}:{self.port}')>"

