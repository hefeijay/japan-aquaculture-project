#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器数据服务模块
负责从数据库获取传感器和传感器读数数据
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, or_

from db_models.db_session import db_session_factory
from db_models.sensor import Sensor
from db_models.sensor_reading import SensorReading
from db_models.sensor_type import SensorType

logger = logging.getLogger(__name__)


class SensorService:
    """传感器数据服务类"""
    
    @classmethod
    def get_all_sensors(cls) -> List[Dict[str, Any]]:
        """
        获取所有传感器信息
        
        Returns:
            传感器信息列表
        """
        try:
            with db_session_factory() as session:
                sensors = session.query(Sensor).join(SensorType).all()
                
                sensor_list = []
                for sensor in sensors:
                    sensor_info = {
                        "id": sensor.id,
                        "sensor_id": sensor.sensor_id,
                        "name": sensor.name,
                        "pond_id": sensor.pond_id,
                        "sensor_type_id": sensor.sensor_type_id,
                        "model": sensor.model,
                        "status": sensor.status,
                        "installed_at": sensor.installed_at.isoformat() if sensor.installed_at else None,
                        "sensor_type_name": sensor.sensor_type.type_name if sensor.sensor_type else None,
                        "unit": sensor.sensor_type.unit if sensor.sensor_type else None
                    }
                    sensor_list.append(sensor_info)
                
                return sensor_list
                
        except Exception as e:
            logger.error(f"获取传感器信息失败: {str(e)}")
            return []
    
    @classmethod
    def get_sensor_readings_by_sensor_id(cls, sensor_id: int, hours: int = 1) -> List[Dict[str, Any]]:
        """
        根据传感器ID获取指定时间范围内的读数数据
        
        Args:
            sensor_id: 传感器ID
            hours: 获取多少小时内的数据，默认1小时
            
        Returns:
            传感器读数数据列表
        """
        try:
            with db_session_factory() as session:
                # 计算时间范围
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                readings = session.query(SensorReading)\
                    .filter(SensorReading.sensor_id == sensor_id)\
                    .filter(SensorReading.recorded_at >= start_time)\
                    .filter(SensorReading.recorded_at <= end_time)\
                    .order_by(SensorReading.recorded_at.desc())\
                    .all()
                
                reading_list = []
                for reading in readings:
                    reading_info = {
                        "id": reading.id,
                        "sensor_id": reading.sensor_id,
                        "value": reading.value,
                        "recorded_at": reading.recorded_at.isoformat(),
                        "created_at": None
                    }
                    reading_list.append(reading_info)
                
                return reading_list
                
        except Exception as e:
            logger.error(f"获取传感器读数失败: {str(e)}")
            return []
    
    @classmethod
    def get_all_sensor_readings(cls, hours: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有传感器的读数数据
        
        Args:
            hours: 获取多少小时内的数据，默认1小时
            
        Returns:
            按传感器类型分组的读数数据字典
        """
        try:
            with db_session_factory() as session:
                # 计算时间范围
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
                
                # 获取所有传感器及其读数
                readings = session.query(SensorReading, Sensor, SensorType)\
                    .join(Sensor, SensorReading.sensor_id == Sensor.id)\
                    .join(SensorType, Sensor.sensor_type_id == SensorType.id)\
                    .filter(SensorReading.recorded_at >= start_time)\
                    .filter(SensorReading.recorded_at <= end_time)\
                    .order_by(SensorReading.recorded_at.desc())\
                    .all()
                
                # 按传感器类型分组
                grouped_readings = {}
                for reading, sensor, sensor_type in readings:
                    type_name = sensor_type.type_name
                    if type_name not in grouped_readings:
                        grouped_readings[type_name] = []
                    
                    reading_info = {
                        "sensor_id": sensor.id,
                        "value": reading.value,
                        "recorded_at": reading.recorded_at.isoformat(),
                        "sensor_name": sensor.name
                    }
                    grouped_readings[type_name].append(reading_info)
                
                return grouped_readings
                
        except Exception as e:
            logger.error(f"获取所有传感器读数失败: {str(e)}")
            return {}
    
    @classmethod
    def get_latest_sensor_readings(cls) -> Dict[str, Any]:
        """
        获取每个传感器的最新读数
        
        Returns:
            每个传感器的最新读数字典
        """
        try:
            with db_session_factory() as session:
                # 获取每个传感器的最新读数
                latest_readings = {}
                sensors = session.query(Sensor).join(SensorType).all()
                
                for sensor in sensors:
                    latest_reading = session.query(SensorReading)\
                        .filter(SensorReading.sensor_id == sensor.id)\
                        .order_by(SensorReading.recorded_at.desc())\
                        .first()
                    
                    if latest_reading:
                        latest_readings[sensor.sensor_type.type_name] = {
                            "value": latest_reading.value,
                            "recorded_at": latest_reading.recorded_at.isoformat(),
                            "sensor_name": sensor.name
                        }
                
                return latest_readings
                
        except Exception as e:
            logger.error(f"获取最新传感器读数失败: {str(e)}")
            return {}
    
    @classmethod
    def has_sensor_data(cls) -> bool:
        """
        检查数据库中是否有传感器数据
        
        Returns:
            是否有传感器数据
        """
        try:
            with db_session_factory() as session:
                count = session.query(SensorReading).count()
                return count > 0
        except Exception as e:
            logger.error(f"检查传感器数据失败: {str(e)}")
            return False
    
    @classmethod
    def get_latest_sensor_readings_by_metric(cls, limit: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取 sensor_types 表中每个 metric 在 sensor_readings 表中相同 metric 值的最新 N 条记录
        
        Args:
            limit: 每个 metric 获取的最新记录数，默认24条
            
        Returns:
            按 metric 分组的读数数据字典，格式：{metric: [reading_info, ...]}
        """
        try:
            with db_session_factory() as session:
                # 获取所有有 metric 值的 sensor_types
                sensor_types = session.query(SensorType)\
                    .filter(SensorType.metric.isnot(None))\
                    .filter(SensorType.metric != '')\
                    .all()
                
                grouped_readings = {}
                
                # 对每个 metric，获取最新的 N 条记录
                for sensor_type in sensor_types:
                    metric = sensor_type.metric
                    if not metric:
                        continue
                    
                    # 获取该 metric 的最新 N 条记录
                    # 使用 COALESCE 优先使用 ts_utc，如果为空则使用 recorded_at，再为空则使用 created_at
                    readings = session.query(SensorReading)\
                        .filter(SensorReading.metric == metric)\
                        .filter(or_(
                            SensorReading.recorded_at.isnot(None),
                            SensorReading.ts_utc.isnot(None),
                            SensorReading.created_at.isnot(None)
                        ))\
                        .order_by(
                            func.coalesce(
                                SensorReading.ts_utc,
                                SensorReading.recorded_at,
                                SensorReading.created_at
                            ).desc()
                        )\
                        .limit(limit)\
                        .all()
                    
                    # 转换为字典格式
                    reading_list = []
                    for reading in readings:
                        # 优先使用 ts_utc，如果为空则使用 recorded_at，再为空则使用 created_at
                        timestamp = reading.ts_utc or reading.recorded_at or reading.created_at
                        reading_info = {
                            "value": reading.value,
                            "recorded_at": timestamp.isoformat() if timestamp else None,
                            "type_name": reading.type_name or sensor_type.type_name,
                            "metric": reading.metric or metric,
                            "unit": reading.unit or sensor_type.unit,
                            "description": reading.description or sensor_type.description
                        }
                        reading_list.append(reading_info)
                    
                    # 使用 metric 作为 key，如果 metric 已存在则合并（去重）
                    if metric in grouped_readings:
                        # 合并并去重（按 recorded_at）
                        existing_dict = {r["recorded_at"]: r for r in grouped_readings[metric]}
                        for r in reading_list:
                            if r["recorded_at"] and r["recorded_at"] not in existing_dict:
                                existing_dict[r["recorded_at"]] = r
                        # 按时间排序并限制数量
                        grouped_readings[metric] = sorted(
                            existing_dict.values(),
                            key=lambda x: x["recorded_at"] if x["recorded_at"] else "",
                            reverse=True
                        )[:limit]
                    else:
                        grouped_readings[metric] = reading_list
                
                return grouped_readings
                
        except Exception as e:
            logger.error(f"按 metric 获取最新传感器读数失败: {str(e)}", exc_info=True)
            return {}