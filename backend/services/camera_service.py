#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头服务类
用于从数据库获取摄像头状态、图片和健康检查数据
适配统一设备表架构（直接从devices表获取摄像头信息）
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import time

from db_models.db_session import db_session_factory
from db_models.camera import CameraImage, CameraHealth
from db_models.device import Device, DeviceType

logger = logging.getLogger(__name__)


class CameraService:
    """摄像头数据服务类"""
    
    @classmethod
    def _translate_status(cls, status: str) -> str:
        """
        翻译设备状态为中文
        只有在线和离线两种状态
        
        Args:
            status: 英文状态
            
        Returns:
            中文状态
        """
        status_map = {
            "online": "在线",
            "offline": "离线"
        }
        return status_map.get(status, "离线")  # 默认返回离线
    
    @classmethod
    def get_camera_status(cls, device_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头状态数据
        
        Args:
            device_id: 设备主键ID (devices.id)
            
        Returns:
            摄像头状态数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                # 直接从devices表查询摄像头设备（过滤已删除的设备）
                device = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.id == device_id)\
                    .filter(Device.is_deleted == False)\
                    .filter(DeviceType.category == 'camera')\
                    .first()
                
                if not device:
                    logger.warning(f"摄像头设备{device_id}不存在或已删除")
                    return None
                
                # 从 device_specific_config 获取摄像头配置
                config = device.device_specific_config or {}
                
                # 转换为字典格式（保持原有字段名）
                status_data = {
                    "id": device.id,
                    "name": device.name,
                    "location": device.location or "",
                    "status": cls._translate_status(device.status),  # 翻译为中文
                    "quality": config.get("quality", "未知"),
                    "resolution": config.get("resolution", "N/A"),
                    "lastUpdate": int(device.updated_at.timestamp() * 1000) if device.updated_at else int(time.time() * 1000),
                    "lastUpdateTime": device.updated_at.strftime("%H:%M:%S") if device.updated_at else datetime.now().strftime("%H:%M:%S"),
                }
                
                logger.info(f"成功获取摄像头设备{device_id}状态数据")
                return status_data
                
        except Exception as e:
            logger.error(f"获取摄像头设备{device_id}状态数据失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def get_camera_image(cls, device_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头图片数据
        
        Args:
            device_id: 设备主键ID (devices.id)
            
        Returns:
            摄像头图片数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                from sqlalchemy import desc
                
                # 直接从devices表查询摄像头设备（过滤已删除的设备）
                device = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.id == device_id)\
                    .filter(Device.is_deleted == False)\
                    .filter(DeviceType.category == 'camera')\
                    .first()
                
                if not device:
                    logger.warning(f"摄像头设备{device_id}不存在或已删除")
                    return None
                
                # 获取最新的图片记录（直接通过device_id查询）
                latest_image = session.query(CameraImage)\
                    .filter(CameraImage.device_id == device_id)\
                    .order_by(desc(CameraImage.ts_utc))\
                    .first()
                
                if not latest_image:
                    logger.warning(f"摄像头设备{device_id}图片数据不存在")
                    return None
                
                # 转换为字典格式（保持原有字段名）
                image_data = {
                    "id": device.id,
                    "name": device.name,
                    "location": device.location or "",
                    "status": cls._translate_status(device.status),  # 翻译为中文
                    "imageUrl": latest_image.image_url,
                    "lastUpdate": int(latest_image.ts_utc.timestamp() * 1000) if latest_image.ts_utc else int(time.time() * 1000),
                    "timestamp": int(latest_image.ts_utc.timestamp() * 1000) if latest_image.ts_utc else int(time.time() * 1000),
                    "timestampStr": latest_image.timestamp_str,
                    "width": latest_image.width,
                    "height": latest_image.height,
                    "format": latest_image.format,
                    "size": latest_image.size
                }
                
                logger.info(f"成功获取摄像头设备{device_id}图片数据")
                return image_data
                
        except Exception as e:
            logger.error(f"获取摄像头设备{device_id}图片数据失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def get_camera_health(cls, device_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头健康检查数据
        
        Args:
            device_id: 设备主键ID (devices.id)
            
        Returns:
            摄像头健康检查数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                from sqlalchemy import desc
                
                # 直接从devices表查询摄像头设备（过滤已删除的设备）
                device = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.id == device_id)\
                    .filter(Device.is_deleted == False)\
                    .filter(DeviceType.category == 'camera')\
                    .first()
                
                if not device:
                    logger.warning(f"摄像头设备{device_id}不存在或已删除")
                    return None
                
                # 获取最新的健康检查记录（直接通过device_id查询）
                latest_health = session.query(CameraHealth)\
                    .filter(CameraHealth.device_id == device_id)\
                    .order_by(desc(CameraHealth.timestamp))\
                    .first()
                
                if not latest_health:
                    logger.warning(f"摄像头设备{device_id}健康检查数据不存在")
                    return None
                
                # 转换为字典格式（保持原有字段名）
                health_data = {
                    "id": device.id,
                    "name": device.name,
                    "location": device.location or "",
                    "health_status": latest_health.health_status,
                    "overall_score": float(latest_health.overall_score),
                    "checks": {
                        "connectivity": {
                            "status": latest_health.connectivity_status,
                            "score": latest_health.connectivity_score,
                            "message": latest_health.connectivity_message
                        },
                        "image_quality": {
                            "status": latest_health.image_quality_status,
                            "score": latest_health.image_quality_score,
                            "message": latest_health.image_quality_message
                        },
                        "hardware": {
                            "status": latest_health.hardware_status,
                            "score": latest_health.hardware_score,
                            "message": latest_health.hardware_message
                        },
                        "storage": {
                            "status": latest_health.storage_status,
                            "score": latest_health.storage_score,
                            "message": latest_health.storage_message
                        }
                    },
                    "timestamp": latest_health.timestamp,
                    "last_check": latest_health.last_check
                }
                
                logger.info(f"成功获取摄像头设备{device_id}健康检查数据")
                return health_data
                
        except Exception as e:
            logger.error(f"获取摄像头设备{device_id}健康检查数据失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def get_camera_list(cls) -> List[Dict[str, Any]]:
        """
        获取所有摄像头设备列表
        
        Returns:
            摄像头列表，包含 id、name、location
        """
        try:
            with db_session_factory() as session:
                # 查询所有未删除的摄像头设备
                devices = session.query(Device)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.is_deleted == False)\
                    .filter(DeviceType.category == 'camera')\
                    .order_by(Device.id)\
                    .all()
                
                camera_list = []
                for device in devices:
                    camera_list.append({
                        "id": device.id,
                        "name": device.name,
                        "location": device.location or ""
                    })
                
                logger.info(f"成功获取{len(camera_list)}个摄像头设备列表")
                return camera_list
                
        except Exception as e:
            logger.error(f"获取摄像头列表失败: {str(e)}", exc_info=True)
            return []
