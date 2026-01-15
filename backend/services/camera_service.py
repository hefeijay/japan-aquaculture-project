#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头服务类
用于从数据库获取摄像头状态、图片和健康检查数据
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
import time

from db_models.db_session import db_session_factory
from db_models.camera import Camera
from db_models.device import Device

logger = logging.getLogger(__name__)


class CameraService:
    """摄像头数据服务类"""
    
    @classmethod
    def get_camera_status(cls, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头状态数据
        
        Args:
            camera_id: 摄像头ID (cameras.id)
            
        Returns:
            摄像头状态数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                # 查询摄像头及其关联的设备信息
                camera_query = session.query(Camera, Device)\
                    .join(Device, Camera.device_id == Device.id)\
                    .filter(Camera.id == camera_id)\
                    .first()
                
                if not camera_query:
                    logger.warning(f"摄像头{camera_id}状态数据不存在")
                    return None
                
                camera, device = camera_query
                
                # 转换为字典格式（保持原有字段名）
                status_data = {
                    "id": camera.id,
                    "name": camera.name,
                    "location": device.location or "",
                    "status": device.status,  # online/offline/maintenance
                    "quality": camera.quality or "未知",
                    "resolution": camera.resolution or "N/A",
                    "fps": camera.fps,
                    "lastUpdate": camera.last_update if camera.last_update else int(time.time() * 1000),
                    "lastUpdateTime": camera.last_update_time if camera.last_update_time else datetime.now().strftime("%H:%M:%S"),
                    "temperature": float(camera.temperature) if camera.temperature else None,
                    "connectivity": camera.connectivity,
                    "recording": camera.recording,
                    "nightVision": camera.night_vision,
                    "motionDetection": camera.motion_detection
                }
                
                logger.info(f"成功获取摄像头{camera_id}状态数据")
                return status_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}状态数据失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def get_camera_image(cls, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头图片数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头图片数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                from db_models.camera import CameraImage
                from sqlalchemy import desc
                
                # 查询摄像头及其最新图片
                camera_query = session.query(Camera, Device)\
                    .join(Device, Camera.device_id == Device.id)\
                    .filter(Camera.id == camera_id)\
                    .first()
                
                if not camera_query:
                    logger.warning(f"摄像头{camera_id}不存在")
                    return None
                
                camera, device = camera_query
                
                # 获取最新的图片记录
                latest_image = session.query(CameraImage)\
                    .filter(CameraImage.camera_id == camera_id)\
                    .order_by(desc(CameraImage.ts_utc))\
                    .first()
                
                if not latest_image:
                    logger.warning(f"摄像头{camera_id}图片数据不存在")
                    return None
                
                # 转换为字典格式（保持原有字段名）
                image_data = {
                    "id": camera.id,
                    "name": camera.name,
                    "location": device.location or "",
                    "status": device.status,
                    "imageUrl": latest_image.image_url,
                    "lastUpdate": int(latest_image.ts_utc.timestamp() * 1000) if latest_image.ts_utc else int(time.time() * 1000),
                    "timestamp": int(latest_image.ts_utc.timestamp() * 1000) if latest_image.ts_utc else int(time.time() * 1000),
                    "timestampStr": latest_image.timestamp_str,
                    "width": latest_image.width,
                    "height": latest_image.height,
                    "format": latest_image.format,
                    "size": latest_image.size
                }
                
                logger.info(f"成功获取摄像头{camera_id}图片数据")
                return image_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}图片数据失败: {str(e)}", exc_info=True)
            return None
    
    @classmethod
    def get_camera_health(cls, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头健康检查数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头健康检查数据字典，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                from db_models.camera import CameraHealth
                from sqlalchemy import desc
                
                # 查询摄像头及其最新健康检查记录
                camera_query = session.query(Camera, Device)\
                    .join(Device, Camera.device_id == Device.id)\
                    .filter(Camera.id == camera_id)\
                    .first()
                
                if not camera_query:
                    logger.warning(f"摄像头{camera_id}不存在")
                    return None
                
                camera, device = camera_query
                
                # 获取最新的健康检查记录
                latest_health = session.query(CameraHealth)\
                    .filter(CameraHealth.camera_id == camera_id)\
                    .order_by(desc(CameraHealth.timestamp))\
                    .first()
                
                if not latest_health:
                    logger.warning(f"摄像头{camera_id}健康检查数据不存在")
                    return None
                
                # 转换为字典格式（保持原有字段名）
                health_data = {
                    "id": camera.id,
                    "name": camera.name,
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
                
                logger.info(f"成功获取摄像头{camera_id}健康检查数据")
                return health_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}健康检查数据失败: {str(e)}", exc_info=True)
            return None