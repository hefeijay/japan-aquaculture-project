#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话模型 (Session Model)
"""
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Index, String, TIMESTAMP, Integer, Text as SQLText
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Session(Base):
    """会话模型"""
    __tablename__ = "session"
    __table_args__ = (
        Index("idx_session_session_id", "session_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[Optional[str]] = mapped_column(SQLText, nullable=True)  # JSON 格式的配置
    status: Mapped[Optional[str]] = mapped_column(String(50), default="active", nullable=True)
    session_name: Mapped[Optional[str]] = mapped_column(String(128), default="new chat", nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, 
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
        name="created_at"  # 明确指定列名，兼容 create_at 和 created_at
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id='{self.user_id}', status='{self.status}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "config": self.config,
            "status": self.status,
            "session_name": self.session_name,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

