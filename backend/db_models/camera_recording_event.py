#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头录制事件模型
用于存储摄像头开始录制和结束录制的事件记录
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .device import Device

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class CameraRecordingEvent(Base):
    """
    摄像头录制事件模型
    记录摄像头的开始录制和结束录制事件
    """
    __tablename__ = "camera_recording_events"
    __table_args__ = (
        Index("idx_cre_device_ts", "device_id", "event_timestamp"),
        Index("idx_cre_event_type", "event_type"),
        Index("idx_cre_filename", "filename"),
        Index("idx_cre_camera_index", "camera_index"),
    )
    
    # 主键ID
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        comment="主键ID",
        init=False
    )
    
    # 摄像头索引（客户端传入的 camera_index）
    camera_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="摄像头索引（客户端传入）"
    )
    
    # 设备ID（FK → devices.id），可选，通过 camera_index 映射获取
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        comment="设备ID（FK → devices.id）",
        init=False
    )
    
    # 事件类型（start_recording/finish_recording）
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="事件类型（start_recording=开始录制/finish_recording=结束录制）"
    )
    
    # 事件时间戳（客户端传入的时间）
    event_timestamp: Mapped[datetime] = mapped_column(
        DATETIME(6),  # 支持微秒精度
        nullable=False,
        comment="事件时间戳（客户端传入）"
    )
    
    # 录制文件名
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="录制文件名"
    )
    
    # 录制时长（秒）
    duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="录制时长（秒）"
    )
    
    # 帧率
    fps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        comment="帧率"
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
    
    # ORM 关系（延迟引用，避免循环导入）
    device: Mapped[Optional["Device"]] = relationship("Device", init=False)

