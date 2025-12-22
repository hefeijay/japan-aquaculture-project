#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from .base import Base


class DeviceType(enum.Enum):
    SENSOR = "sensor"
    CAMERA = "camera"
    FEEDER = "feeder"


class DeviceStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAULT = "fault"


class Device(Base):
    """设备清单"""
    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_devices_type_pool", "type", "pool_id"),
    )
    
    device_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    install_location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    pool_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[DeviceStatus] = mapped_column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.ACTIVE)
    vendor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    calibration_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

