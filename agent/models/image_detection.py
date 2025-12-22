#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像检测结果模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, Integer, TIMESTAMP, ForeignKey, DECIMAL, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class ImageDetection(Base):
    """图像检测汇总结果"""
    __tablename__ = "image_detections"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    frame_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("image_frames.id"), nullable=False)
    ts_utc: Mapped[datetime] = mapped_column(TIMESTAMP(3), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_length_mm: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    avg_height_mm: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    est_weight_g_avg: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    feed_present: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shrimp_shell_present: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence_avg: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

