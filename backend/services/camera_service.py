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

from japan_server.app_factory import create_app
from japan_server.db_models import CameraStatus, CameraImage, CameraHealth, db

logger = logging.getLogger(__name__)


class CameraService:
    """摄像头数据服务类"""
    
    @classmethod
    def get_camera_status(cls, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        从数据库获取摄像头状态数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头状态数据字典，如果不存在返回None
        """
        try:
            # 获取应用上下文
            app = create_app()
            with app.app_context():
                # 查询摄像头状态
                camera_status = db.session.query(CameraStatus).filter_by(camera_id=camera_id).first()
                
                if not camera_status:
                    logger.warning(f"摄像头{camera_id}状态数据不存在")
                    return None
                
                # 转换为字典格式
                status_data = {
                    "id": camera_status.camera_id,
                    "name": camera_status.name,
                    "location": camera_status.location,
                    "status": camera_status.status,
                    "quality": camera_status.quality,
                    "resolution": camera_status.resolution,
                    "fps": camera_status.fps,
                    "lastUpdate": camera_status.last_update,
                    "lastUpdateTime": camera_status.last_update_time,
                    "temperature": float(camera_status.temperature) if camera_status.temperature else None,
                    "connectivity": camera_status.connectivity,
                    "recording": camera_status.recording,
                    "nightVision": camera_status.night_vision,
                    "motionDetection": camera_status.motion_detection
                }
                
                logger.info(f"成功获取摄像头{camera_id}状态数据")
                return status_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}状态数据失败: {str(e)}")
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
            # 获取应用上下文
            app = create_app()
            with app.app_context():
                # 查询摄像头图片
                camera_image = db.session.query(CameraImage).filter_by(camera_id=camera_id).first()
                
                if not camera_image:
                    logger.warning(f"摄像头{camera_id}图片数据不存在")
                    return None
                
                # 转换为字典格式
                image_data = {
                    "id": camera_image.camera_id,
                    "name": camera_image.name,
                    "location": camera_image.location,
                    "status": camera_image.status,
                    "imageUrl": camera_image.image_url,
                    "lastUpdate": camera_image.last_update,
                    "timestamp": camera_image.timestamp,
                    "timestampStr": camera_image.timestamp_str,
                    "width": camera_image.width,
                    "height": camera_image.height,
                    "format": camera_image.format,
                    "size": camera_image.size
                }
                
                logger.info(f"成功获取摄像头{camera_id}图片数据")
                return image_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}图片数据失败: {str(e)}")
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
            # 获取应用上下文
            app = create_app()
            with app.app_context():
                # 查询摄像头健康状态
                camera_health = db.session.query(CameraHealth).filter_by(camera_id=camera_id).first()
                
                if not camera_health:
                    logger.warning(f"摄像头{camera_id}健康检查数据不存在")
                    return None
                
                # 转换为字典格式
                health_data = {
                    "id": camera_health.camera_id,
                    "name": camera_health.name,
                    "location": camera_health.location,
                    "health_status": camera_health.health_status,
                    "overall_score": float(camera_health.overall_score),
                    "checks": {
                        "connectivity": {
                            "status": camera_health.connectivity_status,
                            "score": camera_health.connectivity_score,
                            "message": camera_health.connectivity_message
                        },
                        "image_quality": {
                            "status": camera_health.image_quality_status,
                            "score": camera_health.image_quality_score,
                            "message": camera_health.image_quality_message
                        },
                        "hardware": {
                            "status": camera_health.hardware_status,
                            "score": camera_health.hardware_score,
                            "message": camera_health.hardware_message
                        },
                        "storage": {
                            "status": camera_health.storage_status,
                            "score": camera_health.storage_score,
                            "message": camera_health.storage_message
                        }
                    },
                    "timestamp": camera_health.timestamp,
                    "last_check": camera_health.last_check
                }
                
                logger.info(f"成功获取摄像头{camera_id}健康检查数据")
                return health_data
                
        except Exception as e:
            logger.error(f"获取摄像头{camera_id}健康检查数据失败: {str(e)}")
            return None