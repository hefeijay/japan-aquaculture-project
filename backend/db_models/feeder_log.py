#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机运行记录ORM模型
对应 feeder_logs 表，存储喂食机运行记录
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    DECIMAL,
    Enum,
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
    pond_id为快照字段，优化LLM查询和保证历史数据一致性
    """
    __tablename__ = "feeder_logs"
    __table_args__ = (
        Index("idx_fl_feeder_ts", "feeder_id", "ts_utc"),
        Index("idx_fl_pond_ts", "pond_id", "ts_utc"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 喂食机ID（FK）
    feeder_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("feeders.id"),
        nullable=False,
        comment="喂食机ID（FK）"
    )
    
    # 所属养殖池ID（FK）- 快照字段，记录投喂时的池位，用于历史数据一致性和LLM查询优化
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）- 快照字段，记录投喂时的池位，用于历史数据一致性和LLM查询优化"
    )
    
    # 批次ID（FK）
    batch_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("batches.batch_id"),
        comment="批次ID（FK）",
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
        Enum('ok', 'warning', 'error', name='feeder_status_enum'),
        nullable=False,
        default='ok',
        comment="状态"
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
    feeder: Mapped["Feeder"] = relationship(back_populates="feeder_logs", init=False)
    pond: Mapped["Pond"] = relationship(back_populates="feeder_logs", init=False)
    batch: Mapped[Optional["Batch"]] = relationship(init=False)




