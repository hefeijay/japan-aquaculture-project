#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理中心ORM模型
对应 work_tasks 表，存储人工创建和管理的业务任务信息
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import (
    String,
    TIMESTAMP,
    Integer,
    ForeignKey,
    Index,
    text,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class WorkTask(Base):
    """
    任务管理中心表
    存储人工创建的业务任务，支持优先级、负责人、截止时间、关联池位等管理字段
    """
    __tablename__ = "work_tasks"
    __table_args__ = (
        Index("idx_work_task_task_id", "task_id"),
        Index("idx_work_task_status", "status"),
        Index("idx_work_task_priority", "priority"),
        Index("idx_work_task_assignee", "assignee_id"),
        Index("idx_work_task_pond", "pond_id"),
        Index("idx_work_task_deadline", "deadline"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # ── 必填字段（init 时需传参，无默认值，必须排在最前）──────────────────

    # 任务名称
    topic: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="任务名称"
    )

    # 优先级（high=高/medium=中/low=低）
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="优先级（high=高/medium=中/low=低）"
    )

    # 创建人ID（外键，关联用户表）
    creator_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
        comment="创建人ID（FK → user.id）"
    )

    # ── 自动/可选字段（init=False，排在必填字段之后）─────────────────────

    # 任务业务ID（Service 层自动生成，如：TASK-2026-0001）
    task_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        comment="任务业务ID（自动生成，如：TASK-2026-0001）",
        init=False
    )

    # 任务描述（可选）
    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        comment="任务描述（可选）",
        init=False
    )

    # 状态（pending=待处理/in_progress=进行中/completed=已完成）
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态（pending=待处理/in_progress=进行中/completed=已完成）",
        init=False
    )

    # 负责人ID（外键，关联用户表，可选）
    assignee_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        comment="负责人ID（FK → user.id，可选）",
        init=False
    )

    # 关联池位ID（外键，关联养殖池表，可选）
    pond_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        comment="关联池位ID（FK → ponds.id，可选）",
        init=False
    )

    # 截止时间（可选）
    deadline: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        comment="截止时间（可选）",
        init=False
    )

    # 完成时间（可选）
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        comment="完成时间（可选）",
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

    # ORM 关系定义
    creator: Mapped["User"] = relationship(
        foreign_keys=[creator_id],
        init=False
    )
    assignee: Mapped[Optional["User"]] = relationship(
        foreign_keys=[assignee_id],
        init=False
    )
    pond: Mapped[Optional["Pond"]] = relationship(
        back_populates="work_tasks",
        init=False
    )
