#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警通知ORM模型
对应 alert_notifications 表，存储所有预警通知信息
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
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class AlertNotification(Base):
    """
    预警通知表
    存储所有预警通知信息，关联预警规则和设备
    """
    __tablename__ = "alert_notifications"
    __table_args__ = (
        Index("idx_alert_notification_id", "notification_id"),
        Index("idx_alert_notification_rule", "alert_rule_id"),
        Index("idx_alert_notification_device", "device_id"),
        Index("idx_alert_notification_status", "status"),
        Index("idx_alert_notification_triggered", "triggered_at"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )

    # 预警记录业务ID（唯一标识符，如：REC-001）
    notification_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="预警记录业务ID（唯一标识符，如：REC-001）"
    )

    # 预警规则ID（外键，关联预警规则表）
    alert_rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("alert_rules.id"),
        nullable=False,
        comment="预警规则ID（FK → alert_rules.id）"
    )

    # 设备ID（外键，关联设备表，冗余存储便于查询）
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id，冗余存储便于查询）"
    )

    # 状态（pending=待处理/resolved=已解决）
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="状态（pending=待处理/resolved=已解决）",
        init=False
    )

    # 预警内容（如：电池电量不足，当前值15%）
    content: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="预警内容（如：电池电量不足，当前值15%）"
    )

    # 触发预警时的实际值
    current_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="触发预警时的实际值",
        init=False
    )

    # 预警触发时间
    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        comment="预警触发时间"
    )

    # 解决时间
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP,
        comment="解决时间",
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
    alert_rule: Mapped["AlertRule"] = relationship(back_populates="alert_notifications", init=False)
    device: Mapped["Device"] = relationship(back_populates="alert_notifications", init=False)

