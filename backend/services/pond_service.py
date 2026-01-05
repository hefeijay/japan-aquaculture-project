#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
池塘详情服务模块
负责从数据库获取池塘的详细信息
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from db_models.db_session import db_session_factory
from db_models.pond import Pond
from db_models.batch import Batch
from db_models.sensor_reading import SensorReading
from db_models.sensor import Sensor
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
        获取所有池塘列表
        
        Returns:
            池塘列表，包含 pond_name, pond_id, species_list 等信息
        """
        try:
            with db_session_factory() as session:
                ponds = session.query(Pond).all()
                
                pond_list = []
                for pond in ponds:
                    # 获取当前活跃批次的物种类型
                    species_list = []
                    batch = session.query(Batch)\
                        .filter(Batch.pool_id == str(pond.id))\
                        .filter(Batch.end_date.is_(None))\
                        .order_by(Batch.start_date.desc())\
                        .first()
                    
                    if batch and batch.species:
                        # 如果物种类型是逗号分隔的字符串，拆分成列表
                        if ',' in batch.species:
                            species_list = [s.strip() for s in batch.species.split(',')]
                        else:
                            species_list = [batch.species]
                    
                    pond_info = {
                        "pond_name": pond.name or f"{pond.id}号养殖池",
                        "pond_id": str(pond.id),
                        "species_list": species_list
                    }
                    pond_list.append(pond_info)
                
                return pond_list
                
        except Exception as e:
            logger.error(f"获取池塘列表失败: {str(e)}", exc_info=True)
            return []
    
    @classmethod
    def get_pond_detail(cls, pond_id: str) -> Optional[Dict[str, Any]]:
        """
        获取池塘详细信息
        
        Args:
            pond_id: 池塘ID（字符串）
            
        Returns:
            池塘详情字典，包含池塘信息、传感器数据、批次信息、虾类统计等
        """
        try:
            with db_session_factory() as session:
                pond_id_int = int(pond_id)
                
                # 1. 获取池塘基本信息
                pond = session.query(Pond).filter(Pond.id == pond_id_int).first()
                if not pond:
                    logger.warning(f"池塘 {pond_id} 不存在")
                    return None
                
                # 2. 获取当前活跃批次信息
                batch = session.query(Batch)\
                    .filter(Batch.pool_id == pond_id)\
                    .filter(Batch.end_date.is_(None))\
                    .order_by(Batch.start_date.desc())\
                    .first()
                
                # 如果没有活跃批次，获取最新批次
                if not batch:
                    batch = session.query(Batch)\
                        .filter(Batch.pool_id == pond_id)\
                        .order_by(Batch.start_date.desc())\
                        .first()
                
                # 3. 获取传感器最新读数
                sensors = session.query(Sensor)\
                    .filter(Sensor.pond_id == pond_id_int)\
                    .join(SensorType)\
                    .all()
                
                sensor_data = {}
                for sensor in sensors:
                    latest_reading = session.query(SensorReading)\
                        .filter(SensorReading.sensor_id == sensor.id)\
                        .order_by(SensorReading.recorded_at.desc())\
                        .first()
                    
                    if latest_reading and sensor.sensor_type:
                        type_name = sensor.sensor_type.type_name.lower()
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
                            "number": pond_count,  # 使用 ponds.count 而不是 shrimp_stats.total_live
                        }
                    },
                    "sensor": sensor_data,
                    "environment": {
                        "time": int(datetime.now().timestamp()),
                        "region": pond.location or "筑波",
                        "weather": "sunny",  # 需要从天气API获取，或从环境数据表获取
                        "temperature": sensor_data.get("water_temperature", 25.0)  # 使用水温作为环境温度，或从环境数据获取
                    },
                    "stats_image": {
                        # 图像路径需要根据实际存储位置配置
                        # 可以从配置或数据库获取实际路径
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
        如果池塘不存在，会自动创建新记录
        
        Args:
            pond_id: 池塘ID（字符串），如果池塘不存在会自动创建
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
                
                # 1. 获取或创建池塘基本信息
                pond = session.query(Pond).filter(Pond.id == pond_id_int).first()
                is_new_pond = False
                
                if not pond:
                    # 池塘不存在，创建新记录
                    # 生成默认名称（如果请求中没有提供）
                    pond_name = None
                    if "pond" in detail_data and "name" in detail_data["pond"]:
                        pond_name = detail_data["pond"]["name"]
                    elif "environment" in detail_data and "region" in detail_data["environment"]:
                        # 使用地区信息生成名称
                        region = detail_data["environment"]["region"]
                        pond_name = f"{region}-{pond_id}号养殖池"
                    else:
                        # 默认名称
                        pond_name = f"{pond_id}号养殖池"
                    
                    # 检查名称是否已存在，如果存在则添加后缀
                    existing_pond = session.query(Pond).filter(Pond.name == pond_name).first()
                    if existing_pond:
                        counter = 1
                        while True:
                            new_name = f"{pond_name}-{counter}"
                            if not session.query(Pond).filter(Pond.name == new_name).first():
                                pond_name = new_name
                                break
                            counter += 1
                    
                    # 从请求数据中获取字段值（如果提供）
                    pond_data = detail_data.get("pond", {})
                    pond_location = None
                    if "environment" in detail_data and "region" in detail_data["environment"]:
                        pond_location = detail_data["environment"]["region"]
                    elif "location" in pond_data:
                        pond_location = pond_data["location"]
                    
                    pond_area = pond_data.get("area") if "area" in pond_data else None
                    pond_count = None
                    if "species" in pond_data and "number" in pond_data["species"]:
                        pond_count = pond_data["species"]["number"]
                    
                    pond_description = pond_data.get("description") if "description" in pond_data else None
                    
                    # 创建新池塘
                    # 由于 Pond 使用 MappedAsDataclass，需要在构造函数中提供所有必需字段
                    pond = Pond(
                        name=pond_name,
                        location=pond_location,
                        area=pond_area,
                        count=pond_count,
                        description=pond_description
                    )
                    # 设置 ID（如果数据库允许手动指定自增主键）
                    pond.id = pond_id_int
                    
                    session.add(pond)
                    session.flush()  # 刷新以获取ID
                    is_new_pond = True
                    logger.info(f"创建新池塘: ID={pond_id_int}, name={pond_name}")
                
                updated_fields = []
                
                # 2. 更新池塘基本信息 (pond)
                if "pond" in detail_data:
                    pond_info = detail_data["pond"]
                    
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
                        # 获取当前活跃批次或最新批次
                        batch = session.query(Batch)\
                            .filter(Batch.pool_id == pond_id)\
                            .filter(Batch.end_date.is_(None))\
                            .order_by(Batch.start_date.desc())\
                            .first()
                        
                        if not batch:
                            batch = session.query(Batch)\
                                .filter(Batch.pool_id == pond_id)\
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
                    
                    # 获取该池塘的所有传感器
                    sensors = session.query(Sensor)\
                        .filter(Sensor.pond_id == pond_id_int)\
                        .join(SensorType)\
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
                        .filter(Batch.pool_id == pond_id)\
                        .filter(Batch.end_date.is_(None))\
                        .order_by(Batch.start_date.desc())\
                        .first()
                    batch_id = batch.batch_id if batch else None
                    
                    now = datetime.now()
                    
                    for field_name, value in sensor_data.items():
                        if value is None:
                            continue
                        
                        # 找到对应的传感器
                        target_types = field_to_type_map.get(field_name, [])
                        if isinstance(target_types, str):
                            target_types = [target_types]
                        
                        matched_sensor = None
                        for sensor in sensors:
                            if sensor.sensor_type:
                                type_name_lower = sensor.sensor_type.type_name.lower()
                                if type_name_lower in [t.lower() for t in target_types]:
                                    matched_sensor = sensor
                                    break
                        
                        if matched_sensor:
                            # 创建新的传感器读数记录
                            # 只传入 init=True 的必需参数（sensor_id 和 value）
                            new_reading = SensorReading(
                                sensor_id=matched_sensor.id,
                                value=float(value)
                            )
                            # 设置 init=False 的字段（通过属性赋值）
                            new_reading.recorded_at = now
                            new_reading.ts_utc = now
                            if batch_id:
                                new_reading.batch_id = batch_id
                            new_reading.pool_id = pond_id
                            
                            # 从数据库查询 type_name 对应的 metric
                            sensor_type_name = matched_sensor.sensor_type.type_name
                            metric_from_db = get_metric_from_type_name(session, sensor_type_name)
                            
                            if metric_from_db:
                                new_reading.metric = metric_from_db
                                logger.debug(f"从数据库获取 metric: type_name '{sensor_type_name}' -> metric '{metric_from_db}'")
                            else:
                                # 如果数据库中没有找到 metric，使用 type_name 的小写形式（向后兼容）
                                new_reading.metric = sensor_type_name.lower()
                                logger.debug(f"数据库中没有找到 metric，使用 type_name 小写: '{sensor_type_name.lower()}'")
                            
                            # 设置 type_name 为传感器类型的 type_name
                            new_reading.type_name = sensor_type_name
                            session.add(new_reading)
                            updated_fields.append(f"sensor.{field_name}")
                            logger.info(f"为传感器 {matched_sensor.id} ({matched_sensor.sensor_type.type_name}) 添加新读数: {value}")
                        else:
                            logger.warning(f"未找到字段 {field_name} 对应的传感器")
                
                # 4. 更新环境数据 (environment)
                if "environment" in detail_data:
                    env_data = detail_data["environment"]
                    
                    # 更新位置信息
                    if "region" in env_data:
                        pond.location = env_data["region"]
                        updated_fields.append("location")
                    
                    # 注意：weather 和 temperature 可能需要存储到其他表
                    # 这里先记录日志，后续可以扩展
                    if "weather" in env_data or "temperature" in env_data:
                        logger.info(f"环境数据 weather={env_data.get('weather')}, temperature={env_data.get('temperature')}，暂未存储到数据库")
                
                # 5. 更新统计图像路径 (stats_image)
                if "stats_image" in detail_data:
                    # 图像路径可能需要存储到配置或某个表
                    # 这里先记录日志，后续可以扩展
                    image_data = detail_data["stats_image"]
                    logger.info(f"统计图像路径 length={image_data.get('length')}, weight={image_data.get('weight')}，暂未存储到数据库")
                
                # 提交事务
                session.commit()
                
                if is_new_pond:
                    logger.info(f"成功创建新池塘 {pond_id}，并更新了 {len(updated_fields)} 个字段")
                    # 返回创建后的数据
                    updated_detail = cls.get_pond_detail(pond_id)
                    return True, f"成功创建新池塘并更新 {len(updated_fields)} 个字段", updated_detail
                elif updated_fields:
                    logger.info(f"成功更新池塘 {pond_id} 的以下字段: {', '.join(updated_fields)}")
                    # 返回更新后的数据
                    updated_detail = cls.get_pond_detail(pond_id)
                    return True, f"成功更新 {len(updated_fields)} 个字段", updated_detail
                else:
                    return False, "没有需要更新的字段", None
                
        except Exception as e:
            logger.error(f"更新池塘详情失败: {str(e)}", exc_info=True)
            return False, f"更新失败: {str(e)}", None

