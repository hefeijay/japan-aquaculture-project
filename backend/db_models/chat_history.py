from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
)
from sqlalchemy.dialects.mysql import  TEXT
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"
    __table_args__ = (
        Index("idx_session_id", "session_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)  
    session_id: Mapped[str] = mapped_column(String(128))
    role: Mapped[Optional[str]] = mapped_column(String(32))
    content: Mapped[Optional[str]] = mapped_column(
        TEXT(charset="utf8mb4", collation="utf8mb4_unicode_ci")
    )
    type: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[Optional[str]] = mapped_column(String(50),default="active")
    
    timestamp: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP,default=datetime.now(timezone.utc))
    message_id: Mapped[Optional[str]] = mapped_column(String(128),default=None)
    tool_calls: Mapped[Optional[str]] = mapped_column(
        TEXT(charset="utf8mb4", collation="utf8mb4_unicode_ci"),
        default=None
    )
    meta_data: Mapped[Optional[str]] = mapped_column(
        TEXT(charset="utf8mb4", collation="utf8mb4_unicode_ci"),
        default=None
    )
    updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP,default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc))
