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
from db_models.device import Device, DeviceType
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
                # 查询所有传感器类型的设备
                sensors = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(DeviceType.category == 'sensor')\
                    .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                    .all()
                
                sensor_list = []
                for sensor in sensors:
                    sensor_info = {
                        "id": sensor.id,
                        "sensor_id": sensor.device_id,  # 使用 device_id 替代 sensor_id
                        "name": sensor.name,
                        "pond_id": sensor.pond_id,
                        "sensor_type_id": sensor.sensor_type_id,
                        "model": sensor.model,
                        "status": sensor.status,
                        "installed_at": None,  # Device 表中没有 installed_at 字段
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
        根据传感器ID（设备ID）获取指定时间范围内的读数数据
        
        Args:
            sensor_id: 传感器设备ID
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
                    .filter(SensorReading.device_id == sensor_id)\
                    .filter(or_(
                        SensorReading.recorded_at >= start_time,
                        SensorReading.ts_utc >= start_time,
                        SensorReading.created_at >= start_time
                    ))\
                    .filter(or_(
                        SensorReading.recorded_at <= end_time,
                        SensorReading.ts_utc <= end_time,
                        SensorReading.created_at <= end_time
                    ))\
                    .order_by(
                        func.coalesce(
                            SensorReading.ts_utc,
                            SensorReading.recorded_at,
                            SensorReading.created_at
                        ).desc()
                    )\
                    .all()
                
                reading_list = []
                for reading in readings:
                    timestamp = reading.ts_utc or reading.recorded_at or reading.created_at
                    reading_info = {
                        "id": reading.id,
                        "sensor_id": reading.device_id,  # 使用 device_id
                        "value": reading.value,
                        "recorded_at": timestamp.isoformat() if timestamp else None,
                        "created_at": reading.created_at.isoformat() if reading.created_at else None
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
                
                # 获取所有传感器及其读数（只查询传感器类型的设备）
                readings = session.query(SensorReading, Device, SensorType)\
                    .join(Device, SensorReading.device_id == Device.id)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(DeviceType.category == 'sensor')\
                    .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                    .filter(or_(
                        SensorReading.recorded_at >= start_time,
                        SensorReading.ts_utc >= start_time,
                        SensorReading.created_at >= start_time
                    ))\
                    .filter(or_(
                        SensorReading.recorded_at <= end_time,
                        SensorReading.ts_utc <= end_time,
                        SensorReading.created_at <= end_time
                    ))\
                    .order_by(
                        func.coalesce(
                            SensorReading.ts_utc,
                            SensorReading.recorded_at,
                            SensorReading.created_at
                        ).desc()
                    )\
                    .all()
                
                # 按传感器类型分组
                grouped_readings = {}
                for reading, device, sensor_type in readings:
                    type_name = sensor_type.type_name if sensor_type else "未知类型"
                    if type_name not in grouped_readings:
                        grouped_readings[type_name] = []
                    
                    timestamp = reading.ts_utc or reading.recorded_at or reading.created_at
                    reading_info = {
                        "sensor_id": device.id,
                        "value": reading.value,
                        "recorded_at": timestamp.isoformat() if timestamp else None,
                        "sensor_name": device.name
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
                # 获取每个传感器的最新读数（只查询传感器类型的设备）
                latest_readings = {}
                sensors = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(DeviceType.category == 'sensor')\
                    .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                    .all()
                
                for sensor in sensors:
                    latest_reading = session.query(SensorReading)\
                        .filter(SensorReading.device_id == sensor.id)\
                        .order_by(
                            func.coalesce(
                                SensorReading.ts_utc,
                                SensorReading.recorded_at,
                                SensorReading.created_at
                            ).desc()
                        )\
                        .first()
                    
                    if latest_reading and sensor.sensor_type:
                        timestamp = latest_reading.ts_utc or latest_reading.recorded_at or latest_reading.created_at
                        latest_readings[sensor.sensor_type.type_name] = {
                            "value": latest_reading.value,
                            "recorded_at": timestamp.isoformat() if timestamp else None,
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
    def get_latest_sensor_readings_by_metric(cls, limit: int = 24) -> Dict[str, Dict[str, Any]]:
        """
        获取 sensor_types 表中每个 metric 在 sensor_readings 表中相同 metric 值的最新 N 条记录
        
        Args:
            limit: 每个 metric 获取的最新记录数，默认24条
            
        Returns:
            按 metric 分组的读数数据字典，格式：{metric: {"readings": [...], "valid_min": x, "valid_max": x}}
        """
        try:
            with db_session_factory() as session:
                # 获取所有有 metric 值的 sensor_types
                sensor_types = session.query(SensorType)\
                    .filter(SensorType.metric.isnot(None))\
                    .filter(SensorType.metric != '')\
                    .all()
                
                grouped_readings = {}
                
                # 对每个 metric，通过 JOIN 获取最新的 N 条记录
                for sensor_type in sensor_types:
                    metric = sensor_type.metric
                    if not metric:
                        continue
                    
                    # 通过 JOIN 查询该 metric 对应的所有读数
                    # sensor_readings → devices → device_types (filter category='sensor') → sensor_types
                    # 使用 COALESCE 优先使用 ts_utc，如果为空则使用 recorded_at，再为空则使用 created_at
                    readings = session.query(SensorReading)\
                        .join(Device, SensorReading.device_id == Device.id)\
                        .join(DeviceType, Device.device_type_id == DeviceType.id)\
                        .filter(DeviceType.category == 'sensor')\
                        .outerjoin(SensorType, Device.sensor_type_id == SensorType.id)\
                        .filter(SensorType.metric == metric)\
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
                            "type_name": sensor_type.type_name,  # SensorReading 没有 type_name 字段
                            "metric": metric,
                            "unit": reading.unit or sensor_type.unit,
                            "description": reading.description or sensor_type.description
                        }
                        reading_list.append(reading_info)
                    
                    # 构建包含阈值信息的数据结构
                    metric_data = {
                        "readings": reading_list,
                        "valid_min": float(sensor_type.valid_min) if sensor_type.valid_min is not None else None,
                        "valid_max": float(sensor_type.valid_max) if sensor_type.valid_max is not None else None,
                        "unit": sensor_type.unit,
                        "type_name": sensor_type.type_name
                    }
                    
                    # 使用 metric 作为 key，如果 metric 已存在则合并（去重）
                    if metric in grouped_readings:
                        # 合并并去重（按 recorded_at）
                        existing_dict = {r["recorded_at"]: r for r in grouped_readings[metric]["readings"]}
                        for r in reading_list:
                            if r["recorded_at"] and r["recorded_at"] not in existing_dict:
                                existing_dict[r["recorded_at"]] = r
                        # 按时间排序并限制数量
                        grouped_readings[metric]["readings"] = sorted(
                            existing_dict.values(),
                            key=lambda x: x["recorded_at"] if x["recorded_at"] else "",
                            reverse=True
                        )[:limit]
                    else:
                        grouped_readings[metric] = metric_data
                
                return grouped_readings
                
        except Exception as e:
            logger.error(f"按 metric 获取最新传感器读数失败: {str(e)}", exc_info=True)
            return {}