#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
池塘详情服务模块
负责从数据库获取池塘的详细信息
适配统一设备表架构（直接从devices表获取传感器信息）
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from db_models.db_session import db_session_factory
from db_models.pond import Pond
from db_models.batch import Batch
from db_models.sensor_reading import SensorReading
from db_models.device import Device, DeviceType
from db_models.sensor_type import SensorType
from sqlalchemy import desc, func, text

logger = logging.getLogger(__name__)


def get_metric_from_type_name(session, type_name: str) -> Optional[str]:
    """
    从数据库查询 type_name 对应的 metric
    
    Args:
        session: 数据库会话
        type_name: 传感器类型名称
        
    Returns:
        str: metric 标识符，如果未找到则返回 None
    """
    if not type_name:
        return None
    
    result = session.execute(
        text("""
            SELECT metric 
            FROM sensor_types 
            WHERE type_name = :type_name OR LOWER(type_name) = LOWER(:type_name)
            LIMIT 1
        """),
        {"type_name": type_name}
    ).first()
    
    if result and result[0]:
        return result[0]
    return None


class PondService:
    """池塘详情服务类"""
    
    @classmethod
    def get_pond_list(cls) -> list[Dict[str, Any]]:
        """
        获取所有池塘列表（轻量接口，只返回id和name）
        
        Returns:
            池塘列表，包含 id 和 name
        """
        try:
            with db_session_factory() as session:
                ponds = session.query(Pond).all()
                
                pond_list = []
                for pond in ponds:
                    pond_info = {
                        "id": pond.id,
                        "name": pond.name
                    }
                    pond_list.append(pond_info)
                
                logger.info(f"成功获取 {len(pond_list)} 个池塘列表")
                return pond_list
                
        except Exception as e:
            logger.error(f"获取池塘列表失败: {str(e)}", exc_info=True)
            return []
    
    @classmethod
    def get_pond_detail(cls, pond_id: str) -> Optional[Dict[str, Any]]:
        """
        获取池塘详细信息
        
        Args:
            pond_id: 池塘主键ID（字符串格式的整数，如 "1", "2"）
            
        Returns:
            池塘详情字典，包含池塘信息、传感器数据、批次信息、虾类统计等
        """
        try:
            with db_session_factory() as session:
                pond_id_int = int(pond_id)
                
                # 1. 获取池塘基本信息（通过主键ID查询）
                pond = session.query(Pond).filter(Pond.id == pond_id_int).first()
                if not pond:
                    logger.warning(f"池塘 {pond_id} 不存在")
                    return None
                
                # 2. 获取当前活跃批次信息
                batch = session.query(Batch)\
                    .filter(Batch.pond_id == pond_id_int)\
                    .filter(Batch.end_date.is_(None))\
                    .order_by(Batch.start_date.desc())\
                    .first()
                
                # 如果没有活跃批次，获取最新批次
                if not batch:
                    batch = session.query(Batch)\
                        .filter(Batch.pond_id == pond_id_int)\
                        .order_by(Batch.start_date.desc())\
                        .first()
                
                # 3. 获取传感器最新读数（从统一设备表查询）
                # 查询该池塘的所有传感器设备（过滤已删除的设备）
                sensor_devices = session.query(Device, SensorType)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                    .filter(Device.pond_id == pond_id_int)\
                    .filter(Device.is_deleted == False)\
                    .filter(DeviceType.category == 'sensor')\
                    .all()
                
                sensor_data = {}
                for device, sensor_type in sensor_devices:
                    # 获取最新读数（直接通过device_id查询）
                    latest_reading = session.query(SensorReading)\
                        .filter(SensorReading.device_id == device.id)\
                        .order_by(SensorReading.recorded_at.desc())\
                        .first()
                    
                    if latest_reading and sensor_type:
                        type_name = sensor_type.type_name.lower()
                        # 映射传感器类型名称到接口字段名
                        field_map = {
                            "temperature": "water_temperature",
                            "ph": "pH",
                            "dissolved_oxygen_aturation": "Dissolved_oxygen",
                            "dissolved_oxygen_saturation": "Dissolved_oxygen",
                            "liquid_level": "liquid_level",
                            "turbidity": "Turbidity",
                        }
                        
                        field_name = field_map.get(type_name, type_name)
                        sensor_data[field_name] = float(latest_reading.value)
                
                # 4. 构建响应数据
                # 从 ponds 表获取 area 和 count
                pond_area = float(pond.area) if pond.area is not None else 20.0
                pond_count = int(pond.count) if pond.count is not None else 0
                
                detail = {
                    "pond": {
                        "area": pond_area,
                        "species": {
                            "type": "shrimp" if batch and "shrimp" in batch.species.lower() else (batch.species if batch else "shrimp"),
                            "number": pond_count,
                        }
                    },
                    "sensor": sensor_data,
                    "environment": {
                        "time": int(datetime.now().timestamp()),
                        "region": pond.location or "筑波",
                        "weather": "sunny",
                        "temperature": sensor_data.get("water_temperature", 25.0)
                    },
                    "stats_image": {
                        "length": f"http://8.216.33.92:5000/static/pond_images/length/live_shrimp_size_distribution_{pond_id}.png",
                        "weight": f"http://8.216.33.92:5000/static/pond_images/weight/live_shrimp_weight_distribution_{pond_id}.png"
                    }
                }
                
                result = {
                    "pond_name": pond.name,
                    "pond_id": pond_id,
                    "detail": detail
                }
                
                logger.info(f"成功获取池塘 {pond_id} 的详细信息")
                return result
                
        except Exception as e:
            logger.error(f"获取池塘详情失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def update_pond_detail(cls, pond_id: str, detail_data: Dict[str, Any]) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        更新池塘详细信息（支持部分更新）
        池塘必须已存在，否则返回错误
        
        Args:
            pond_id: 池塘主键ID（字符串格式的整数，如 "1", "2"）
            detail_data: 要更新的数据字典，包含以下可选字段：
                - pond: {name, area, species: {type, number}}
                - sensor: {water_temperature, pH, Dissolved_oxygen, liquid_level, Turbidity}
                - environment: {time, region, weather, temperature}
                - stats_image: {length, weight}
            
        Returns:
            tuple: (是否成功, 消息, 更新后的数据)
        """
        try:
            with db_session_factory() as session:
                pond_id_int = int(pond_id)
                
                # 1. 获取池塘基本信息（通过主键ID查询）
                pond = session.query(Pond).filter(Pond.id == pond_id_int).first()
                
                if not pond:
                    logger.warning(f"池塘 {pond_id} 不存在，无法更新")
                    return False, f"池塘 {pond_id} 不存在", None
                
                updated_fields = []
                
                # 2. 更新池塘基本信息 (pond)
                if "pond" in detail_data:
                    pond_info = detail_data["pond"]
                    
                    # 更新名称
                    if "name" in pond_info:
                        pond.name = pond_info["name"]
                        updated_fields.append("name")
                    
                    # 更新描述
                    if "description" in pond_info:
                        pond.description = pond_info["description"]
                        updated_fields.append("description")
                    
                    # 更新面积
                    if "area" in pond_info:
                        pond.area = float(pond_info["area"])
                        updated_fields.append("area")
                    
                    # 更新数量
                    if "species" in pond_info and "number" in pond_info["species"]:
                        pond.count = int(pond_info["species"]["number"])
                        updated_fields.append("count")
                    
                    # 更新物种类型（更新到批次表）
                    if "species" in pond_info and "type" in pond_info["species"]:
                        species_type = pond_info["species"]["type"]
                        batch = session.query(Batch)\
                            .filter(Batch.pond_id == pond_id_int)\
                            .filter(Batch.end_date.is_(None))\
                            .order_by(Batch.start_date.desc())\
                            .first()
                        
                        if not batch:
                            batch = session.query(Batch)\
                                .filter(Batch.pond_id == pond_id_int)\
                                .order_by(Batch.start_date.desc())\
                                .first()
                        
                        if batch:
                            batch.species = species_type
                            updated_fields.append("batch.species")
                        else:
                            logger.warning(f"池塘 {pond_id} 没有找到批次信息，无法更新物种类型")
                
                # 3. 更新传感器数据 (sensor)
                if "sensor" in detail_data:
                    sensor_data = detail_data["sensor"]
                    
                    # 获取该池塘的所有传感器设备（从统一设备表查询，过滤已删除的设备）
                    sensor_devices = session.query(Device, SensorType)\
                        .join(DeviceType, Device.device_type_id == DeviceType.id)\
                        .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                        .filter(Device.pond_id == pond_id_int)\
                        .filter(Device.is_deleted == False)\
                        .filter(DeviceType.category == 'sensor')\
                        .all()
                    
                    # 创建传感器类型名称到字段名的反向映射
                    field_to_type_map = {
                        "water_temperature": "temperature",
                        "pH": "ph",
                        "Dissolved_oxygen": ["dissolved_oxygen_aturation", "dissolved_oxygen_saturation"],
                        "liquid_level": "liquid_level",
                        "Turbidity": "turbidity",
                    }
                    
                    # 获取当前批次ID（用于插入传感器读数）
                    batch = session.query(Batch)\
                        .filter(Batch.pond_id == pond_id_int)\
                        .filter(Batch.end_date.is_(None))\
                        .order_by(Batch.start_date.desc())\
                        .first()
                    batch_id = batch.id if batch else None
                    
                    now = datetime.now()
                    
                    for field_name, value in sensor_data.items():
                        if value is None:
                            continue
                        
                        # 找到对应的传感器设备
                        target_types = field_to_type_map.get(field_name, [])
                        if isinstance(target_types, str):
                            target_types = [target_types]
                        
                        matched_device = None
                        matched_sensor_type = None
                        for device, sensor_type in sensor_devices:
                            if sensor_type:
                                type_name_lower = sensor_type.type_name.lower()
                                if type_name_lower in [t.lower() for t in target_types]:
                                    matched_device = device
                                    matched_sensor_type = sensor_type
                                    break
                        
                        if matched_device and matched_sensor_type:
                            # 创建新的传感器读数记录
                            new_reading = SensorReading(
                                device_id=matched_device.id,  # 直接使用device.id
                                pond_id=pond_id_int,
                                value=float(value)
                            )
                            # 设置 init=False 的字段
                            new_reading.recorded_at = now
                            new_reading.ts_utc = now
                            if batch_id:
                                new_reading.batch_id = batch_id
                            
                            # 从数据库查询 type_name 对应的 metric
                            sensor_type_name = matched_sensor_type.type_name
                            metric_from_db = get_metric_from_type_name(session, sensor_type_name)
                            
                            if metric_from_db:
                                new_reading.metric = metric_from_db
                                logger.debug(f"从数据库获取 metric: type_name '{sensor_type_name}' -> metric '{metric_from_db}'")
                            else:
                                new_reading.metric = sensor_type_name.lower()
                                logger.debug(f"数据库中没有找到 metric，使用 type_name 小写: '{sensor_type_name.lower()}'")
                            
                            session.add(new_reading)
                            updated_fields.append(f"sensor.{field_name}")
                            logger.info(f"为传感器设备 {matched_device.id} ({matched_sensor_type.type_name}) 添加新读数: {value}")
                        else:
                            logger.warning(f"未找到字段 {field_name} 对应的传感器设备")
                
                # 4. 更新环境数据 (environment)
                if "environment" in detail_data:
                    env_data = detail_data["environment"]
                    
                    # 更新位置信息
                    if "region" in env_data:
                        pond.location = env_data["region"]
                        updated_fields.append("location")
                    
                    if "weather" in env_data or "temperature" in env_data:
                        logger.info(f"环境数据 weather={env_data.get('weather')}, temperature={env_data.get('temperature')}，暂未存储到数据库")
                
                # 5. 更新统计图像路径 (stats_image)
                if "stats_image" in detail_data:
                    image_data = detail_data["stats_image"]
                    logger.info(f"统计图像路径 length={image_data.get('length')}, weight={image_data.get('weight')}，暂未存储到数据库")
                
                # 提交事务
                session.commit()
                
                if updated_fields:
                    logger.info(f"成功更新池塘 {pond_id} 的以下字段: {', '.join(updated_fields)}")
                    # 返回更新后的数据
                    updated_detail = cls.get_pond_detail(pond_id)
                    return True, f"成功更新 {len(updated_fields)} 个字段", updated_detail
                else:
                    return False, "没有需要更新的字段", None
                
        except Exception as e:
            logger.error(f"更新池塘详情失败: {str(e)}", exc_info=True)
            return False, f"更新失败: {str(e)}", None
