#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型数据库模型
用于存储AI模型信息（如 gpt-4o, gpt-4o-mini 等）
"""

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Model(Base):
    """
    AI模型表
    存储可用的AI模型信息
    """
    __tablename__ = "models"
    __table_args__ = (
        Index("idx_model_id", "model_id"),
        Index("idx_status", "status"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        init=False,
        comment="自增主键ID"
    )
    
    # 没有默认值的字段必须在前
    model_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="模型名称，如 gpt-4o, gpt-4o-mini"
    )
    
    description: Mapped[str] = mapped_column(
        String(1024), 
        nullable=False,
        comment="模型描述"
    )
    
    # 有默认值的字段在后
    model_id: Mapped[str] = mapped_column(
        String(36), 
        default=lambda: str(uuid.uuid4()), 
        nullable=False, 
        unique=True, 
        index=True,
        comment="模型唯一标识ID"
    )
    
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="activate",
        comment="模型状态：activate, deactivate"
    )
    
    perm: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="public",
        comment="权限类型：public, private"
    )
    
    created_at: Mapped[Optional[TIMESTAMP]] = mapped_column(
        TIMESTAMP,
        default=datetime.now(timezone.utc),
        comment="创建时间"
    )
    
    updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(
        TIMESTAMP,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="更新时间"
    )
