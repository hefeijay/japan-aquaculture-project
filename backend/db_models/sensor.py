from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import ( 
    Index, 
    String, 
    TIMESTAMP, 
    Integer, 
    ForeignKey, 
    Float,
    text,
) 
from sqlalchemy.orm import Mapped, mapped_column, relationship 
from .base import Base 


class Sensor(Base): 
    """ 
    传感器扩展表
    存储传感器实例特有信息。通过device_id关联devices表，同时冗余存储name/pond_id便于快速查询
    """ 
    __tablename__ = "sensors" 
    __table_args__ = ( 
        Index("idx_sensor_type", "sensor_type_id"),
        Index("idx_sensor_pond", "pond_id"),
    ) 
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False) 
    
    # 关联设备ID（FK）- 一对一关系
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id"),
        unique=True,
        nullable=False,
        comment="关联设备ID（FK）"
    )
    
    # ===== 冗余字段（快照字段，从 devices 同步，便于查询） =====
    # 设备名称（快照字段）
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="设备名称（快照字段，从devices同步）"
    )
    
    # 所属养殖池ID（快照字段）
    pond_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ponds.id"),
        comment="所属养殖池ID（快照字段，从devices同步）"
    )
    # ===== 冗余字段结束 =====
    
    # 传感器类型ID（FK → sensor_types.id）
    sensor_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sensor_types.id"),
        nullable=False,
        comment="传感器类型ID（FK → sensor_types.id）"
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
    device: Mapped["Device"] = relationship(back_populates="sensor", init=False)
    sensor_type: Mapped["SensorType"] = relationship(back_populates="sensors", init=False)
    pond: Mapped[Optional["Pond"]] = relationship(init=False)
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="sensor", cascade="all, delete-orphan", init=False)