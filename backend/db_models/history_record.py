#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
往期养殖记录ORM模型
对应 history_records 表，存储往期养殖记录（结构化）
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    Text,
    TIMESTAMP,
    Index,
    Integer,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME
from .base import Base


class HistoryRecord(Base):
    """
    往期养殖记录表（结构化）
    存储往期养殖记录，包括指标名称、值、单位、时间戳等
    """
    __tablename__ = "history_records"
    __table_args__ = (
        Index("idx_hr_batch_metric_ts", "batch_id", "metric_name", "ts_utc"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 批次ID（FK）
    batch_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        comment="批次ID（FK）",
        init=False
    )
    
    # 指标名称
    metric_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="指标名称"
    )
    
    # 值（文本存储）
    value: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="值（文本存储）"
    )
    
    # 单位
    unit: Mapped[Optional[str]] = mapped_column(
        String(16),
        comment="单位",
        init=False
    )
    
    # UTC时间戳
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="UTC时间戳",
        init=False
    )
    
    # 本地时间戳
    ts_local: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="本地时间戳",
        init=False
    )
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="备注",
        init=False
    )
    
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="创建时间",
        init=False
    )
    
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
        comment="更新时间",
        init=False
    )




