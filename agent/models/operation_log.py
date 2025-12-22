#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作日志模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class OperationLog(Base):
    """操作日志"""
    __tablename__ = "operations_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    batch_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("batches.batch_id"), nullable=True)
    pool_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ts_utc: Mapped[datetime] = mapped_column(TIMESTAMP(3), nullable=False)
    ts_local: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(3), nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachment_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

