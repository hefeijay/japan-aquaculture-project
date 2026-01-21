#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机运行记录ORM模型
对应 feeder_logs 表，存储喂食机运行记录
直接关联devices.id
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    DECIMAL,
    Text,
    TIMESTAMP,
    Index,
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import DATETIME
from .base import Base


class FeederLog(Base):
    """
    喂食机运行记录表
    直接关联devices.id。pond_id为快照字段，优化LLM查询和保证历史数据一致性
    """
    __tablename__ = "feeder_logs"
    __table_args__ = (
        Index("idx_feeder_log_device_ts", "device_id", "ts_utc"),
        Index("idx_feeder_log_pond_ts", "pond_id", "ts_utc"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 设备ID（FK → devices.id）- 直接关联统一设备表
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id）"
    )
    
    # 所属养殖池ID（FK）- 快照字段，记录投喂时的池位
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）- 快照字段，记录投喂时的池位"
    )
    
    # 批次ID（FK，关联到batches表的主键id）
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("batches.id"),
        comment="批次ID（FK，关联到batches.id主键）",
        init=False
    )
    
    # UTC时间戳
    ts_utc: Mapped[datetime] = mapped_column(
        DATETIME(3),
        nullable=False,
        comment="UTC时间戳"
    )
    
    # 本地时间戳
    ts_local: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="本地时间戳",
        init=False
    )
    
    # 投喂量（克）
    feed_amount_g: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(12, 3),
        comment="投喂量（克）",
        init=False
    )
    
    # 运行时长（秒）
    run_time_s: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="运行时长（秒）",
        init=False
    )
    
    # 状态（ok/warning/error）
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='ok',
        comment="状态（ok/warning/error）"
    )
    
    # 剩余饵料估计（克）
    leftover_estimate_g: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(12, 3),
        comment="剩余饵料估计（克）",
        init=False
    )
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="备注",
        init=False
    )
    
    # 完整性校验
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="完整性校验",
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
    
    # ORM 关系
    device: Mapped["Device"] = relationship(back_populates="feeder_logs", init=False)
    pond: Mapped["Pond"] = relationship(back_populates="feeder_logs", init=False)
    batch: Mapped[Optional["Batch"]] = relationship(init=False)
