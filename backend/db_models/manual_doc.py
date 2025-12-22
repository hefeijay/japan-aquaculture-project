#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
养殖手册文档ORM模型
对应 manuals_docs 表，存储养殖手册/文档索引
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
from .base import Base


class ManualDoc(Base):
    """
    养殖手册/文档索引表
    存储养殖手册、文档的URI、版本、来源等信息
    """
    __tablename__ = "manuals_docs"
    __table_args__ = (
        Index("idx_md_version", "version"),
        Index("idx_md_created", "created_at"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 文档URI
    doc_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="文档URI"
    )
    
    # 版本
    version: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="版本",
        init=False
    )
    
    # 来源
    source: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="来源",
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
    
    # 备注
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="备注",
        init=False
    )




