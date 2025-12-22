#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
往期养殖记录模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class HistoryRecord(Base):
    """往期养殖记录"""
    __tablename__ = "history_records"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("batches.batch_id"), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ts_utc: Mapped[datetime] = mapped_column(TIMESTAMP(3), nullable=False)
    ts_local: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

