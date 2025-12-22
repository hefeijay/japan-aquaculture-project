#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库数据库模型
用于存储知识库和文档信息
"""

import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class KnowledgeBase(Base):
    """
    知识库表
    存储知识库的基本信息
    """
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_kb_id", "knowledge_base_id"),
        Index("idx_name", "knowledge_base_name"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        init=False,
        comment="自增主键ID"
    )
    
    # 没有默认值的字段必须在前
    knowledge_base_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="知识库名称"
    )
    
    # 有默认值的字段在后
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), 
        default=lambda: str(uuid.uuid4()), 
        nullable=False, 
        unique=True, 
        index=True,
        comment="知识库唯一标识ID"
    )
    
    # Optional 字段需要显式设置 default=None
    description: Mapped[Optional[str]] = mapped_column(
        String(1024),
        default=None,
        comment="知识库描述"
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
    
    # 关联文档（使用 init=False 避免 dataclass 字段顺序问题）
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        init=False
    )


class KnowledgeDocument(Base):
    """
    知识库文档表
    存储知识库中的文档信息
    """
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("idx_kb_id", "knowledge_base_id"),
        Index("idx_doc_name", "document_name"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        init=False,
        comment="自增主键ID"
    )
    
    # 没有默认值的字段必须在前
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_bases.knowledge_base_id", ondelete="CASCADE"),
        nullable=False,
        comment="所属知识库ID"
    )
    
    document_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="文档名称"
    )
    
    # Optional 字段需要显式设置 default=None
    document_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        default=None,
        comment="文档存储路径"
    )
    
    document_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        default=None,
        comment="文档类型：txt, pdf, docx 等"
    )
    
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=None,
        comment="文件大小（字节）"
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
    
    # 关联知识库（使用 init=False 避免 dataclass 字段顺序问题）
    knowledge_base: Mapped["KnowledgeBase"] = relationship(
        "KnowledgeBase",
        back_populates="documents",
        init=False
    )

