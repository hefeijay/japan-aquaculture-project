#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警规则ORM模型
对应 alert_rules 表，存储设备预警规则配置
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import (
    String,
    TIMESTAMP,
    Integer,
    ForeignKey,
    Boolean,
    Index,
    text,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class AlertRule(Base):
    """
    预警规则表
    存储设备的预警规则配置，包括检测指标、触发条件、报警阈值等
    """
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("idx_alert_rule_device", "device_id"),
        Index("idx_alert_rule_id", "rule_id"),
        Index("idx_alert_rule_severity", "severity_level"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )

    # 设备ID（外键，关联设备表）
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id）"
    )

    # 规则业务ID（唯一标识符，如：AT-001）
    rule_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="规则业务ID（唯一标识符，如：AT-001）"
    )

    # 检测指标（如：battery_level, temperature, dissolved_oxygen等）
    metric: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="检测指标（如：battery_level, temperature, dissolved_oxygen等）"
    )

    # 严重级别（info=信息/warning=警告/critical=严重）
    severity_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="严重级别（info=信息/warning=警告/critical=严重）"
    )

    # 触发判定（below=低于/above=高于）
    trigger_condition: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="触发判定（below=低于/above=高于）"
    )

    # 报警阈值（字符串存储，灵活适配不同指标）
    threshold: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="报警阈值（字符串存储，灵活适配不同指标）"
    )

    # 检测间隔数值（默认5）
    check_interval: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="检测间隔数值（如 5, 10, 30）",
        init=False
    )

    # 检测间隔单位（默认分钟）
    check_interval_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="minute",
        comment="检测间隔单位（minute=分钟/hour=小时/day=天）",
        init=False
    )

    # 是否启用（默认启用）
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用（默认True）",
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
    device: Mapped["Device"] = relationship(back_populates="alert_rules", init=False)
    alert_notifications: Mapped[List["AlertNotification"]] = relationship(
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        init=False
    )

