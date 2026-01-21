#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头数据库模型
用于存储和管理摄像头图片和健康检查数据
直接关联devices.id，不再使用cameras扩展表
"""

from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
    BIGINT,
    BigInteger,
    DECIMAL,
    Boolean,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.mysql import TEXT, DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class CameraImage(Base):
    """
    摄像头图片模型
    直接关联devices.id。pond_id为快照字段，优化LLM查询和保证历史数据一致性
    """
    __tablename__ = "camera_images"
    __table_args__ = (
        Index("idx_camera_image_device_ts", "device_id", "ts_utc"),
        Index("idx_camera_image_pond_ts", "pond_id", "ts_utc"),
        Index("idx_camera_image_batch_ts", "batch_id", "ts_utc"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True, 
        autoincrement=True, 
        comment="主键ID",
        init=False
    )
    
    # 设备ID（FK → devices.id）- 直接关联统一设备表
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id）"
    )
    
    # 所属养殖池ID（FK）- 快照字段，记录拍摄时的池位
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）- 快照字段，记录拍摄时的池位"
    )
    
    # 批次ID（FK，关联到batches表的主键id）
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("batches.id"),
        comment="批次ID（FK，关联到batches.id主键）",
        init=False
    )
    
    # 图片URL
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="图片URL"
    )
    
    # 对象存储路径/URI
    storage_uri: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="对象存储路径/URI",
        init=False
    )
    
    # UTC时间戳
    ts_utc: Mapped[datetime] = mapped_column(
        DATETIME(3),
        nullable=False,
        comment="UTC时间戳"
    )
    
    # 本地时间戳（日本时区）
    ts_local: Mapped[Optional[datetime]] = mapped_column(
        DATETIME(3),
        comment="本地时间戳（日本时区）",
        init=False
    )
    
    # 图片时间戳字符串
    timestamp_str: Mapped[str] = mapped_column(
        String(50),
        default="",
        comment="图片时间戳字符串"
    )
    
    # 图片宽度（像素）
    width: Mapped[int] = mapped_column(
        Integer,
        default=1920,
        comment="图片宽度（像素）"
    )
    
    # 图片高度（像素）
    height: Mapped[int] = mapped_column(
        Integer,
        default=1080,
        comment="图片高度（像素）"
    )
    
    # 图片格式(jpg/png等)
    format: Mapped[str] = mapped_column(
        String(20),
        default="jpg",
        comment="图片格式(jpg/png等)"
    )
    
    # 图片大小(字节)
    size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="图片大小(字节)"
    )
    
    # 编解码
    codec: Mapped[Optional[str]] = mapped_column(
        String(32),
        comment="编解码",
        init=False
    )
    
    # 帧率
    fps: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="帧率"
    )
    
    # 质量标记（ok/missing/anomaly）
    quality_flag: Mapped[str] = mapped_column(
        String(20),
        default='ok',
        nullable=False,
        comment="质量标记（ok/missing/anomaly）",
        init=False
    )
    
    # 完整性校验
    checksum: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="完整性校验",
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
    device: Mapped["Device"] = relationship(back_populates="camera_images", init=False)
    pond: Mapped["Pond"] = relationship(back_populates="camera_images", init=False)
    batch: Mapped[Optional["Batch"]] = relationship(init=False)


class CameraHealth(Base):
    """
    摄像头健康检查模型
    直接关联devices.id。pond_id为快照字段，优化LLM查询和保证历史数据一致性
    """
    __tablename__ = "camera_health"
    __table_args__ = (
        Index("idx_camera_health_device_ts", "device_id", "timestamp"),
        Index("idx_camera_health_pond_ts", "pond_id", "timestamp"),
        Index("idx_camera_health_status", "health_status"),
        Index("idx_ch_overall_score", "overall_score"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        comment="主键ID",
        init=False
    )
    
    # 设备ID（FK → devices.id）- 直接关联统一设备表
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        nullable=False,
        comment="设备ID（FK → devices.id）"
    )
    
    # 所属养殖池ID（FK）- 快照字段，记录检查时的池位
    pond_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        nullable=False,
        comment="所属养殖池ID（FK）- 快照字段，记录检查时的池位"
    )
    
    # 健康状态
    health_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="健康状态(优秀/良好/一般/需要维护/离线)"
    )
    
    # 总体健康分数
    overall_score: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        nullable=False,
        comment="总体健康分数(0-100)"
    )
    
    # 连通性检查状态
    connectivity_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="连通性检查状态"
    )
    
    # 连通性分数
    connectivity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="连通性分数"
    )
    
    # 连通性消息
    connectivity_message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="连通性检查消息"
    )
    
    # 图像质量检查状态
    image_quality_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="图像质量检查状态"
    )
    
    # 图像质量分数
    image_quality_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="图像质量分数"
    )
    
    # 图像质量消息
    image_quality_message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="图像质量检查消息"
    )
    
    # 硬件检查状态
    hardware_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="硬件检查状态"
    )
    
    # 硬件分数
    hardware_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="硬件分数"
    )
    
    # 硬件消息
    hardware_message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="硬件检查消息"
    )
    
    # 存储检查状态
    storage_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="存储检查状态"
    )
    
    # 存储分数
    storage_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="存储分数"
    )
    
    # 存储检查消息
    storage_message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="存储检查消息"
    )
    
    # 检查时间戳(毫秒)
    timestamp: Mapped[int] = mapped_column(
        BIGINT,
        nullable=False,
        comment="检查时间戳(毫秒)"
    )
    
    # 最后检查时间字符串
    last_check: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="最后检查时间字符串"
    )
    
    # 温度
    temperature: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        comment="温度",
        init=False
    )
    
    # 运行时间(小时)
    uptime_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="运行时间(小时)",
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
    device: Mapped["Device"] = relationship(back_populates="camera_health", init=False)
    pond: Mapped["Pond"] = relationship(back_populates="camera_health", init=False)
