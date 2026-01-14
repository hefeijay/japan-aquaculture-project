#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
操作日志ORM模型
对应 operations_logs 表，存储人工操作日志
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
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import DATETIME
from .base import Base


class OperationLog(Base):
    """
    人工操作日志表
    存储人工操作记录，包括操作人、操作类型、备注等
    """
    __tablename__ = "operations_logs"
    __table_args__ = (
        Index("idx_ol_user_ts", "user_id", "ts_utc"),
        Index("idx_ol_batch_ts", "batch_id", "ts_utc"),
        Index("idx_ol_pond_ts", "pond_id", "ts_utc"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 操作用户ID（外键）
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
        comment="操作用户ID（FK）"
    )
    
    # 批次ID（FK，关联到batches表的主键id）
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("batches.id"),
        comment="批次ID（FK，关联到batches.id主键）",
        init=False
    )
    
    # 所属养殖池ID（FK）
    pond_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        comment="所属养殖池ID（FK）",
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
    
    # 操作类型（投料/水质调控/巡检/清洗等）
    action_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="操作类型（投料/水质调控/巡检/清洗等）"
    )
    
    # 备注
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="备注",
        init=False
    )
    
    # 附件URI
    attachment_uri: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="附件URI",
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
    user: Mapped["User"] = relationship(back_populates="operation_logs", init=False)
    pond: Mapped[Optional["Pond"]] = relationship(init=False)
    batch: Mapped[Optional["Batch"]] = relationship(init=False)




