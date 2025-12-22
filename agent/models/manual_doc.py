#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
养殖手册文档模型
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class ManualDoc(Base):
    """养殖手册文档"""
    __tablename__ = "manuals_docs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

