#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机记录模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, TIMESTAMP, ForeignKey, Index, DECIMAL, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class FeederLog(Base):
    """喂食机运行记录"""
    __tablename__ = "feeders_logs"
    __table_args__ = (
        Index("idx_fl_feeder_ts", "feeder_id", "ts_utc"),
        Index("idx_fl_batch_ts", "batch_id", "ts_utc"),
    )
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    feeder_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.device_id"), nullable=False)
    batch_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("batches.batch_id"), nullable=True)
    pool_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ts_utc: Mapped[datetime] = mapped_column(TIMESTAMP(3), nullable=False)
    ts_local: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    feed_amount_g: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 3), nullable=True)
    run_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    leftover_estimate_g: Mapped[Optional[float]] = mapped_column(DECIMAL(12, 3), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

