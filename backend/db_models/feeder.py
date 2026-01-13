#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机扩展表ORM模型
对应 feeders 表，存储喂食机特有信息和云端同步配置
"""

from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Integer,
    String,
    DECIMAL,
    TIMESTAMP,
    text,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Feeder(Base):
    """
    喂食机扩展表
    存储喂食机特有信息和云端同步配置。feed_count等字段从云端API同步，feed_portion_weight为本地配置
    """
    __tablename__ = "feeders"
    __table_args__ = (
        Index("idx_feeder_group", "group_id"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
        init=False
    )
    
    # 关联设备ID（FK）- 一对一关系，通过此ID关联获取name/pond_id/status等基础信息
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        unique=True,
        nullable=False,
        comment="关联设备ID（FK）- 一对一关系，通过此ID关联获取name/pond_id/status等基础信息"
    )
    
    # 云端同步配置
    # 默认喂食份数（来自云端API的feedCount）
    feed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="默认喂食份数（来自云端API的feedCount）"
    )
    
    # 时区（UTC+，对应云端API的devTimeZone）
    timezone: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=9,
        comment="时区（UTC+，对应云端API的devTimeZone）",
        init=False
    )
    
    # 网络类型（0=WiFi, 1=4G，对应云端API的netType）
    network_type: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=0,
        comment="网络类型（0=WiFi, 1=4G，对应云端API的netType）",
        init=False
    )
    
    # 设备分组ID（对应云端API的groupID）
    group_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="设备分组ID（对应云端API的groupID）",
        init=False
    )
    
    # 本地业务配置
    # 每份饲料重量（克）- 本地配置，用于计算总投喂量
    feed_portion_weight: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 1),
        nullable=False,
        default=17.0,
        comment="每份饲料重量（克）- 本地配置，用于计算总投喂量"
    )
    
    # 饲料容量（千克）
    capacity_kg: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        comment="饲料容量（千克）",
        init=False
    )
    
    # 饲料类型
    feed_type: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="饲料类型",
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
    
    # ORM 关系
    device: Mapped["Device"] = relationship(back_populates="feeder", init=False)
    feeder_logs: Mapped[list["FeederLog"]] = relationship(back_populates="feeder", cascade="all, delete-orphan", init=False)

