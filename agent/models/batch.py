#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次信息模型
"""
from typing import Optional
from datetime import date, datetime
from sqlalchemy import Column, BigInteger, String, Date, Text, TIMESTAMP, Index, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Batch(Base):
    """养殖批次信息"""
    __tablename__ = "batches"
    __table_args__ = (
        Index("idx_batches_pool_dates", "pool_id", "start_date", "end_date"),
    )
    
    batch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    species: Mapped[str] = mapped_column(String(64), nullable=False, default="Litopenaeus vannamei")
    pool_id: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    seed_origin: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stocking_density: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

