from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timezone 

from sqlalchemy import ( 
    Index, 
    String, 
    TIMESTAMP, 
    Integer, 
    ForeignKey, 
    text,
    Float
) 
from sqlalchemy.dialects.mysql import TEXT 
from sqlalchemy.orm import Mapped, mapped_column, relationship 
from .base import Base 


class Pond(Base): 
    """ 
    养殖池信息表 
    """ 
    __tablename__ = "ponds" 
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False) 
    
    # 养殖池的唯一标识或名称，方便人类阅读 
    name: Mapped[str] = mapped_column(String(128), unique=True, comment="养殖池名称") 
    
    # 养殖池的地理位置或其他描述信息 
    location: Mapped[Optional[str]] = mapped_column(String(255), comment="位置信息") 
    
    # 养殖池的实际面积（平方米）
    area: Mapped[Optional[float]] = mapped_column(Float, comment="养殖池实际面积（平方米）")
    
    # 养殖池实际统计的数量（尾数）
    count: Mapped[Optional[int]] = mapped_column(Integer, comment="养殖池实际统计的数量（尾数）")
    
    # 备注信息 
    description: Mapped[Optional[str]] = mapped_column(TEXT, comment="描述/备注") 
    
    # 记录创建和更新时间 
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
    # # ORM 关系：一个养殖池可以有多个传感器 
    # sensors: Mapped[list["Sensor"]] = relationship(back_populates="pond", cascade="all, delete-orphan", init=False)
    # ORM 关系定义
    batches: Mapped[List["Batch"]] = relationship(back_populates="pond", init=False)
    devices: Mapped[List["Device"]] = relationship(back_populates="pond", init=False)
    sensor_readings: Mapped[List["SensorReading"]] = relationship(back_populates="pond", init=False)
    feeder_logs: Mapped[List["FeederLog"]] = relationship(back_populates="pond", init=False)
    camera_images: Mapped[List["CameraImage"]] = relationship(back_populates="pond", init=False)
    camera_health: Mapped[List["CameraHealth"]] = relationship(back_populates="pond", init=False)
    shrimp_stats: Mapped[List["ShrimpStats"]] = relationship(back_populates="pond", init=False)
    operation_logs: Mapped[List["OperationLog"]] = relationship(back_populates="pond", init=False)
    # tasks: Mapped[List["Task"]] = relationship(back_populates="pond", init=False)