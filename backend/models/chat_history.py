#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话历史记录模型 - 匹配现有数据库表结构
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, TIMESTAMP, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ChatHistory(Base):
    """对话历史记录 - 匹配现有数据库表结构"""
    __tablename__ = "chat_history"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # user 或 assistant
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 消息内容（数据库字段名）
    message_type: Mapped[Optional[str]] = mapped_column("type", String(50), nullable=True)  # 消息类型（数据库字段名为 type）
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 状态
    timestamp: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)  # 时间戳（数据库字段名）
    message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 消息ID
    tool_calls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 工具调用信息
    meta_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 元数据（数据库字段名为 meta_data）
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)  # 更新时间
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "message": self.content or "",  # 兼容属性：message 映射到 content
            "content": self.content,  # 原始字段
            "type": self.message_type,  # 使用 message_type 属性
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.timestamp.isoformat() if self.timestamp else None,  # 兼容属性：created_at 映射到 timestamp
            "message_id": self.message_id,
            "tool_calls": self.tool_calls,
            "metadata": self.meta_data,  # 兼容属性：metadata 映射到 meta_data
            "meta_data": self.meta_data,  # 原始字段
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# 在类定义后添加兼容属性（避免 SQLAlchemy 元类处理冲突）
def _get_message(self) -> str:
    """兼容属性：返回 content 字段的值"""
    return self.content or ""

def _get_created_at(self) -> Optional[datetime]:
    """兼容属性：返回 timestamp 字段的值"""
    return self.timestamp

def _get_metadata(self) -> Optional[str]:
    """兼容属性：返回 meta_data 字段的值"""
    return self.meta_data

# 添加兼容属性
ChatHistory.message = property(_get_message)
ChatHistory.created_at = property(_get_created_at)
ChatHistory.metadata = property(_get_metadata)
