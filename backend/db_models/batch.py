#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次信息ORM模型
对应 batches 表，存储养殖批次信息
"""

from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    String,
    DECIMAL,
    Date,
    Text,
    TIMESTAMP,
    Index,
    Integer,
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Batch(Base):
    """
    批次信息表
    存储养殖批次的基本信息，包括物种、养殖池、放养密度、起止日期等
    """
    __tablename__ = "batches"
    __table_args__ = (
        Index("idx_batches_pond_dates", "pond_id", "start_date", "end_date"),
    )
    
    # 批次ID（主键）
    batch_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="批次ID（主键）",
        init=False
    )
    
    # 所属养殖池ID（外键，必填字段）
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('ponds.id'),
        nullable=False,
        comment="所属养殖池ID（FK）"
    )
    
    # 开始日期（必填字段）
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="开始日期"
    )
    
    # 物种（默认南美白对虾学名，使用init=False避免dataclass问题）
    species: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        server_default="Litopenaeus vannamei",
        comment="物种（默认南美白对虾学名）",
        init=False
    )
    
    # 场地/车间位置
    location: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="场地/车间位置",
        init=False
    )
    
    # 苗种来源
    seed_origin: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="苗种来源",
        init=False
    )
    
    # 放养密度（尾/㎡或尾/m³）
    stocking_density: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        comment="放养密度（尾/㎡或尾/m³）",
        init=False
    )
    
    # 结束日期（可空）
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        comment="结束日期（可空）",
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
    
    # ORM 关系：关联到养殖池
    pond: Mapped["Pond"] = relationship(back_populates="batches", init=False)

