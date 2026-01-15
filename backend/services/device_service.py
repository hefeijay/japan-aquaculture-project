#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备数据服务模块
负责从数据库获取设备状态和配置信息
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

from db_models.db_session import db_session_factory
from db_models.device import Device, DeviceType
from db_models.sensor import Sensor
from db_models.sensor_type import SensorType
from db_models.feeder import Feeder
from db_models.camera import Camera
from db_models.sensor_reading import SensorReading
from sqlalchemy import desc

logger = logging.getLogger(__name__)


# 设备状态颜色映射
DEVICE_STATUS_COLORS = {
    "online": "#20B2AA",
    "offline": "#ff6b35",
    "maintenance": "#ffa500",
    "standby": "#41b3d3"
}

# 设备类型映射（从 category 到前端显示类型）
DEVICE_TYPE_MAP = {
    "sensor": "sensor",
    "feeder": "feeder",
    "camera": "camera",
    "aerator": "aerator",
    "pump": "pump",
    "filter": "filter",
    "sterilizer": "sterilizer",
    "generator": "generator",
    "monitor": "monitor"
}


class DeviceService:
    """设备数据服务类"""
    
    @classmethod
    def get_all_devices_status(cls) -> List[Dict[str, Any]]:
        """
        获取所有设备的状态信息
        
        Returns:
            设备状态数据列表
        """
        try:
            with db_session_factory() as session:
                # 查询所有设备及其类型
                devices = session.query(Device, DeviceType)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .all()
                
                devices_data = []
                
                for device, device_type in devices:
                    # 基础设备信息
                    device_data = {
                        "id": f"device_{device.id}",
                        "device_id": device.device_id,
                        "name": device.name,
                        "type": DEVICE_TYPE_MAP.get(device_type.category, device_type.category),
                        "category": device_type.category,
                        "type_name": device_type.name,
                        "status": cls._translate_status(device.status),
                        "statusColor": DEVICE_STATUS_COLORS.get(device.status, "#808080"),
                        "parameters": {},
                        "lastUpdate": int(device.updated_at.timestamp() * 1000) if device.updated_at else int(time.time() * 1000),
                        "lastUpdateTime": device.updated_at.strftime("%H:%M:%S") if device.updated_at else datetime.now().strftime("%H:%M:%S"),
                        "location": device.location or "",
                        "pond_id": device.pond_id
                    }
                    
                    # 根据设备类型获取特定参数
                    if device_type.category == "sensor":
                        device_data["parameters"] = cls._get_sensor_parameters(session, device.id)
                    elif device_type.category == "feeder":
                        device_data["parameters"] = cls._get_feeder_parameters(session, device.id)
                    elif device_type.category == "camera":
                        device_data["parameters"] = cls._get_camera_parameters(session, device.id)
                    else:
                        # 其他设备类型从 config_json 获取参数
                        if device.config_json:
                            device_data["parameters"] = device.config_json
                    
                    devices_data.append(device_data)
                
                logger.info(f"成功获取{len(devices_data)}个设备的状态信息")
                return devices_data
                
        except Exception as e:
            logger.error(f"获取设备状态信息失败: {str(e)}", exc_info=True)
            return []
    
    @classmethod
    def _translate_status(cls, status: str) -> str:
        """
        翻译设备状态为中文
        
        Args:
            status: 英文状态
            
        Returns:
            中文状态
        """
        status_map = {
            "online": "运行中",
            "offline": "离线",
            "maintenance": "维护中",
            "standby": "待机"
        }
        return status_map.get(status, status)
    
    @classmethod
    def _get_sensor_parameters(cls, session, device_id: int) -> Dict[str, Any]:
        """
        获取传感器设备的参数信息
        
        Args:
            session: 数据库会话
            device_id: 设备ID
            
        Returns:
            传感器参数字典
        """
        try:
            # 查询传感器信息
            sensor = session.query(Sensor, SensorType)\
                .join(SensorType, Sensor.sensor_type_id == SensorType.id)\
                .filter(Sensor.device_id == device_id)\
                .first()
            
            if not sensor:
                return {}
            
            sensor_obj, sensor_type = sensor
            
            # 获取最新读数
            latest_reading = session.query(SensorReading)\
                .filter(SensorReading.sensor_id == sensor_obj.id)\
                .order_by(desc(SensorReading.recorded_at))\
                .first()
            
            parameters = {
                "sensor_type": sensor_type.type_name,
                "metric": sensor_type.metric,
                "unit": sensor_type.unit,
                "valid_range": f"{sensor_type.valid_min} - {sensor_type.valid_max}" if sensor_type.valid_min is not None else "N/A"
            }
            
            if latest_reading:
                parameters["latest_value"] = float(latest_reading.value)
                parameters["latest_reading_time"] = latest_reading.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if latest_reading.recorded_at else "N/A"
            
            return parameters
            
        except Exception as e:
            logger.error(f"获取传感器参数失败: {str(e)}")
            return {}
    
    @classmethod
    def _get_feeder_parameters(cls, session, device_id: int) -> Dict[str, Any]:
        """
        获取喂食机设备的参数信息
        
        Args:
            session: 数据库会话
            device_id: 设备ID
            
        Returns:
            喂食机参数字典
        """
        try:
            # 查询喂食机信息
            feeder = session.query(Feeder)\
                .filter(Feeder.device_id == device_id)\
                .first()
            
            if not feeder:
                return {}
            
            parameters = {
                "feed_count": feeder.feed_count,
                "feed_portion_weight": float(feeder.feed_portion_weight) if feeder.feed_portion_weight else 0,
                "capacity_kg": float(feeder.capacity_kg) if feeder.capacity_kg else 0,
                "remaining": "N/A"  # 需要计算剩余量
            }
            
            # 如果有容量和使用记录，可以计算剩余量
            if feeder.capacity_kg:
                parameters["schedule"] = "正常"
            
            return parameters
            
        except Exception as e:
            logger.error(f"获取喂食机参数失败: {str(e)}")
            return {}
    
    @classmethod
    def _get_camera_parameters(cls, session, device_id: int) -> Dict[str, Any]:
        """
        获取摄像头设备的参数信息
        
        Args:
            session: 数据库会话
            device_id: 设备ID
            
        Returns:
            摄像头参数字典
        """
        try:
            # 查询摄像头信息
            camera = session.query(Camera)\
                .filter(Camera.device_id == device_id)\
                .first()
            
            if not camera:
                return {}
            
            parameters = {
                "quality": camera.quality or "未知",
                "connectivity": camera.connectivity,
                "temperature": float(camera.temperature) if camera.temperature else None,
                "recording": camera.recording if hasattr(camera, 'recording') else False,
                "resolution": f"{camera.resolution_width}x{camera.resolution_height}" if hasattr(camera, 'resolution_width') else "N/A"
            }
            
            return parameters
            
        except Exception as e:
            logger.error(f"获取摄像头参数失败: {str(e)}")
            return {}
    
    @classmethod
    def get_device_by_id(cls, device_id: str) -> Optional[Dict[str, Any]]:
        """
        根据设备ID获取单个设备的详细信息
        
        Args:
            device_id: 设备唯一标识符
            
        Returns:
            设备详细信息字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                device_query = session.query(Device, DeviceType)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.device_id == device_id)\
                    .first()
                
                if not device_query:
                    logger.warning(f"设备{device_id}不存在")
                    return None
                
                device, device_type = device_query
                
                # 构建设备详细信息
                device_info = {
                    "id": device.id,
                    "device_id": device.device_id,
                    "name": device.name,
                    "description": device.description,
                    "ownership": device.ownership,
                    "type": device_type.name,
                    "category": device_type.category,
                    "model": device.model,
                    "manufacturer": device.manufacturer,
                    "serial_number": device.serial_number,
                    "location": device.location,
                    "pond_id": device.pond_id,
                    "status": device.status,
                    "control_mode": device.control_mode,
                    "firmware_version": device.firmware_version,
                    "hardware_version": device.hardware_version,
                    "ip_address": device.ip_address,
                    "mac_address": device.mac_address,
                    "config": device.config_json,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None
                }
                
                logger.info(f"成功获取设备{device_id}的详细信息")
                return device_info
                
        except Exception as e:
            logger.error(f"获取设备{device_id}详细信息失败: {str(e)}", exc_info=True)
            return None

