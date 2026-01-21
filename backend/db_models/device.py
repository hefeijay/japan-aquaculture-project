from typing import Optional, List
from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Index,
    String,
    TIMESTAMP,
    Integer,
    ForeignKey,
    Float,
    text,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Device(Base):
    """
    统一设备管理表
    管理所有类型的设备。通过device_type_id关联device_types表获取类型信息。
    sensor_type_id仅当设备为传感器时填写，设备专属配置统一存储在device_specific_config JSON字段中
    """
    __tablename__ = "devices"
    __table_args__ = (
        Index("idx_device_status", "status"),
        Index("idx_device_ownership", "ownership"),
        Index("idx_device_type_status", "device_type_id", "status"),
        Index("idx_device_sensor_type", "sensor_type_id"),
        Index("idx_device_pond_status", "pond_id", "status"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)

    # 设备唯一标识符（UUID或序列号）
    device_id: Mapped[str] = mapped_column(
        String(128), 
        unique=True, 
        nullable=False,
        comment="设备唯一标识符（如：feeder_124314, sensor_1343）"
    )

    # 设备名称
    name: Mapped[str] = mapped_column(
        String(128), 
        nullable=False,
        comment="设备名称（必填）"
    )

    # 设备归属（用户、部门、项目等）
    ownership: Mapped[str] = mapped_column(
        String(128), 
        nullable=False,
        comment="设备归属"
    )

    # 设备类型ID（外键，关联设备类型表）
    device_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("device_types.id"),
        nullable=False,
        comment="设备类型ID（FK → device_types.id）"
    )

    # 传感器类型ID（FK → sensor_types.id，仅当category=sensor时填写）
    sensor_type_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sensor_types.id"),
        comment="传感器类型ID（FK → sensor_types.id，仅当category=sensor时填写）"
    )

    # 关联养殖池ID（如果适用）
    pond_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        comment="所属养殖池ID（FK）"
    )

    # 设备安装位置描述
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="设备安装位置"
    )

    # 设备型号/规格
    model: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="设备型号/规格"
    )

    # 制造商信息
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(128),
        comment="制造商"
    )

    # 设备序列号
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(128),
        unique=True,
        comment="设备序列号"
    )

    # 设备连接信息（JSON格式，包含连接地址、账户名、密码等）
    connection_info: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=None,
        comment="设备连接信息（JSON格式），包含连接地址、账户名、密码等连接相关配置"
    )

    # 设备状态（online=在线/offline=离线，默认：online）
    status: Mapped[str] = mapped_column(
        String(50), 
        default="online", 
        nullable=False,
        comment="设备状态（online=在线/offline=离线，默认：online）"
    )

    # 控制权限模式（manual_only=仅人工/ai_only=仅AI/hybrid=人工+AI协同，默认：hybrid）
    control_mode: Mapped[str] = mapped_column(
        String(20),
        default="hybrid",
        nullable=False,
        comment="控制权限模式（manual_only=仅人工/ai_only=仅AI/hybrid=人工+AI协同，默认：hybrid）"
    )

    # 设备专属配置参数（JSON格式）
    device_specific_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=None,
        comment="设备专属配置（JSON格式），不同设备类型存储不同字段，详见设计说明文档"
    )

    # 设备标签（便于分类和搜索）
    tags: Mapped[Optional[str]] = mapped_column(
        String(255),
        default=None,
        comment="设备标签（逗号分隔字符串）"
    )

    # 设备描述
    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        default=None,
        comment="设备描述信息"
    )

    #软删除
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否软删除"
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
    device_type: Mapped[Optional["DeviceType"]] = relationship(back_populates="devices", init=False)
    sensor_type: Mapped[Optional["SensorType"]] = relationship(back_populates="devices", init=False)
    pond: Mapped[Optional["Pond"]] = relationship(back_populates="devices", init=False)
    
    # 日志表关系
    sensor_readings: Mapped[List["SensorReading"]] = relationship(back_populates="device", cascade="all, delete-orphan", init=False)
    feeder_logs: Mapped[List["FeederLog"]] = relationship(back_populates="device", cascade="all, delete-orphan", init=False)
    camera_images: Mapped[List["CameraImage"]] = relationship(back_populates="device", cascade="all, delete-orphan", init=False)
    camera_health: Mapped[List["CameraHealth"]] = relationship(back_populates="device", cascade="all, delete-orphan", init=False)


class DeviceType(Base):
    """
    设备类型字典表
    定义设备类型和大类，避免数据冗余，便于集中管理
    """
    __tablename__ = "device_types"
    __table_args__ = (
        Index("idx_device_type_category", "category"),
    )

    # 主键ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False)

    # 设备大类
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="设备大类（sensor=传感器/feeder=喂食机/camera=摄像头/water_pump=循环水泵/air_blower=鼓风机/water_switch=水龙头开关/solar_heater_pump=太阳能加热器循环泵）"
    )

    # 设备类型名称（中文）
    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="设备类型名称（如：溶解氧传感器、自动喂食机）"
    )

    # 设备类型描述
    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        comment="设备类型描述"
    )

    # 记录创建和更新时间
    created_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, default=lambda: datetime.now(timezone.utc), comment="创建时间", init=False)
    updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), comment="更新时间", init=False)

    # ORM 关系定义
    devices: Mapped[List["Device"]] = relationship(back_populates="device_type", init=False)
