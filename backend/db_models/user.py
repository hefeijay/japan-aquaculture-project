#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户模型
对应 users 表（注意：表名为复数形式），存储系统用户信息
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class User(Base):
    """
    用户信息表
    存储系统用户的基本信息、角色和状态
    """
    __tablename__ = "user"  # 保持原表名，避免破坏现有数据
    __table_args__ = (
        Index("idx_user_user_id", "user_id"),
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_status", "status"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 用户唯一标识ID（业务ID）
    user_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        comment="用户唯一标识ID"
    )
    
    # 用户名（唯一）
    username: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        comment="用户名（唯一）"
    )
    
    # 密码哈希值
    password_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="密码哈希值"
    )
    
    # 角色（admin=管理员/employee=员工/user=普通用户）
    role: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="角色（admin=管理员/employee=员工/user=普通用户）"
    )
    
    # 邮箱（唯一）
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        comment="邮箱（唯一）",
        init=False
    )
    
    # 电话（唯一）
    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        unique=True,
        comment="电话（唯一）",
        init=False
    )
    
    # 状态（active=活跃/inactive=未激活/suspended=已暂停）
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        comment="状态（active=活跃/inactive=未激活/suspended=已暂停）"
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
    operation_logs: Mapped[List["OperationLog"]] = relationship(back_populates="user", init=False)
    
