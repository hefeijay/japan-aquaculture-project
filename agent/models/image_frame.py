#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像帧模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, TIMESTAMP, ForeignKey, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base
from .sensor_reading import QualityFlag


class ImageFrame(Base):
    """图像帧与元数据"""
    __tablename__ = "image_frames"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.device_id"), nullable=False)
    batch_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("batches.batch_id"), nullable=True)
    pool_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ts_utc: Mapped[datetime] = mapped_column(TIMESTAMP(3), nullable=False)
    ts_local: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    storage_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    width_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    codec: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    quality_flag: Mapped[QualityFlag] = mapped_column(Enum(QualityFlag), nullable=False, default=QualityFlag.OK)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

