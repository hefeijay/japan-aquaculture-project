from typing import Optional
from sqlalchemy import (
    String,
    Integer,
)
from sqlalchemy.dialects.mysql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class SensorType(Base): 
    """ 
    传感器测量类型定义表 
    例如：溶解氧饱和度、PH值、浊度等 
    """ 
    __tablename__ = "sensor_types" 
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, init=False) 
    
    # 测量类型的名称 
    type_name: Mapped[str] = mapped_column(String(128), unique=True, comment="类型名称, 如: 溶解氧饱和度") 
    
    # metric 标识符（用于接收数据时的映射，如: temperature, do, ph, water_level, turbidity）
    metric: Mapped[Optional[str]] = mapped_column(String(64), unique=True, comment="metric 标识符，用于数据接收时的映射")
    
    # 数据的单位 
    unit: Mapped[Optional[str]] = mapped_column(String(50), comment="数据单位, 如: %、mm、°C、NTU") 
    
    # 备注信息 
    description: Mapped[Optional[str]] = mapped_column(TEXT, comment="描述/备注") 

    # ORM 关系：一个类型可以对应多个传感器设备 
    sensors: Mapped[list["Sensor"]] = relationship(back_populates="sensor_type", init=False)