#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备数据服务模块
负责从数据库获取设备状态和配置信息
适配统一设备表架构（devices表直接存储所有设备信息）
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time
import random

from db_models.db_session import db_session_factory
from db_models.device import Device, DeviceType
from db_models.sensor_type import SensorType
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
    "water_pump": "pump",
    "air_blower": "aerator",
    "water_switch": "switch",
    "solar_heater_pump": "heater",
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
        获取所有设备的状态信息（过滤已软删除的设备）
        
        返回格式：
        {
            "id": "device_001",
            "name": "增氧机-1号",
            "type": "aerator",
            "status": "运行中",
            "parameters": { ... },
            "lastUpdate": 1704067200000,
            "lastUpdateTime": "2024-01-01 12:00:00"
        }
        
        Returns:
            设备状态数据列表
        """
        try:
            with db_session_factory() as session:
                # 查询所有未删除的设备及其类型
                devices = session.query(Device, DeviceType)\
                    .join(DeviceType, Device.device_type_id == DeviceType.id)\
                    .filter(Device.is_deleted == False)\
                    .all()
                
                devices_data = []
                
                for device, device_type in devices:
                    # 构建 parameters，包含位置等额外信息
                    parameters = device.device_specific_config.copy() if device.device_specific_config else {}
                    
                    # 将位置、养殖池等信息放入 parameters
                    if device.location:
                        parameters["location"] = device.location
                    if device.pond_id:
                        parameters["pond_id"] = device.pond_id
                    if device.model:
                        parameters["model"] = device.model
                    if device.manufacturer:
                        parameters["manufacturer"] = device.manufacturer
                    
                    # 传感器设备将传感器类型信息扁平化到 parameters
                    if device_type.category == "sensor":
                        sensor_info = cls._get_sensor_type_info(session, device)
                        if sensor_info:
                            # 将 sensor_info 的所有字段扁平化到 parameters 中
                            parameters["sensor_type_id"] = sensor_info.get("sensor_type_id")
                            parameters["sensor_type_name"] = sensor_info.get("sensor_type_name")
                            parameters["metric"] = sensor_info.get("metric")
                            parameters["unit"] = sensor_info.get("unit")
                            parameters["valid_min"] = sensor_info.get("valid_min")
                            parameters["valid_max"] = sensor_info.get("valid_max")
                            parameters["description"] = sensor_info.get("description")
                            if "latest_value" in sensor_info:
                                parameters["latest_value"] = sensor_info.get("latest_value")
                            if "latest_reading_time" in sensor_info:
                                parameters["latest_reading_time"] = sensor_info.get("latest_reading_time")
                    
                    # 基础设备信息（精简格式）
                    device_data = {
                        "id": device.device_id,  # 使用设备唯一标识符
                        "name": device.name,
                        "type": DEVICE_TYPE_MAP.get(device_type.category, device_type.category),
                        "status": cls._translate_status(device.status),
                        "parameters": parameters,
                        "lastUpdate": int(device.updated_at.timestamp() * 1000) if device.updated_at else int(time.time() * 1000),
                        "lastUpdateTime": device.updated_at.strftime("%Y-%m-%d %H:%M:%S") if device.updated_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    devices_data.append(device_data)
                
                # 随机选择5个设备返回
                if len(devices_data) > 5:
                    devices_data = random.sample(devices_data, 5)
                
                logger.info(f"成功获取{len(devices_data)}个设备的状态信息（随机选择）")
                return devices_data
                
        except Exception as e:
            logger.error(f"获取设备状态信息失败: {str(e)}", exc_info=True)
            return []
    
    @classmethod
    def _translate_status(cls, status: str) -> str:
        """
        翻译设备状态为中文
        在线=运行中, 离线=待机
        
        Args:
            status: 英文状态
            
        Returns:
            中文状态
        """
        status_map = {
            "online": "运行中",
            "offline": "待机",
            "maintenance": "维护中",
            "standby": "待机"
        }
        return status_map.get(status, status)
    
    @classmethod
    def _get_sensor_type_info(cls, session, device: Device) -> Optional[Dict[str, Any]]:
        """
        获取传感器设备的传感器类型信息
        从devices表的sensor_type_id关联sensor_types表获取
        
        Args:
            session: 数据库会话
            device: 设备对象
            
        Returns:
            传感器类型信息字典
        """
        try:
            if not device.sensor_type_id:
                return None
            
            sensor_type = session.query(SensorType)\
                .filter(SensorType.id == device.sensor_type_id)\
                .first()
            
            if not sensor_type:
                return None
            
            info = {
                "sensor_type_id": sensor_type.id,
                "sensor_type_name": sensor_type.type_name,
                "metric": sensor_type.metric,
                "unit": sensor_type.unit,
                "valid_min": float(sensor_type.valid_min) if sensor_type.valid_min is not None else None,
                "valid_max": float(sensor_type.valid_max) if sensor_type.valid_max is not None else None,
                "description": sensor_type.description
            }
            
            # 获取最新读数（直接通过device.id查询）
            latest_reading = session.query(SensorReading)\
                .filter(SensorReading.device_id == device.id)\
                .order_by(desc(SensorReading.recorded_at))\
                .first()
            
            if latest_reading:
                info["latest_value"] = float(latest_reading.value)
                info["latest_reading_time"] = latest_reading.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if latest_reading.recorded_at else None
            
            return info
            
        except Exception as e:
            logger.error(f"获取传感器类型信息失败: {str(e)}")
            return None
    
    @classmethod
    def get_device_by_id(cls, device_id: str) -> Optional[Dict[str, Any]]:
        """
        根据设备ID获取单个设备的详细信息（过滤已软删除的设备）
        
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
                    .filter(Device.is_deleted == False)\
                    .first()
                
                if not device_query:
                    logger.warning(f"设备{device_id}不存在或已删除")
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
                    "connection_info": device.connection_info,
                    "device_specific_config": device.device_specific_config,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None
                }
                
                # 如果是传感器，添加sensor_type的info信息
                if device_type.category == "sensor":
                    device_info["info"] = cls._get_sensor_type_info(session, device)
                
                logger.info(f"成功获取设备{device_id}的详细信息")
                return device_info
                
        except Exception as e:
            logger.error(f"获取设备{device_id}详细信息失败: {str(e)}", exc_info=True)
            return None

    @classmethod
    def get_device_by_db_id(cls, db_id: int) -> Optional[Device]:
        """
        根据数据库主键ID获取设备对象（过滤已软删除的设备）
        
        Args:
            db_id: 设备数据库主键ID
            
        Returns:
            设备对象，如果不存在返回None
        """
        try:
            with db_session_factory() as session:
                device = session.query(Device)\
                    .filter(Device.id == db_id)\
                    .filter(Device.is_deleted == False)\
                    .first()
                return device
        except Exception as e:
            logger.error(f"获取设备失败: {str(e)}")
            return None


class DeviceConnectionTester:
    """
    设备连接测试服务类
    支持不同类型设备的连接测试，使用策略模式根据 category 分发到对应的测试方法
    """
    
    # 支持的设备类别 -> 测试方法映射
    TESTER_MAP = {
        'feeder': '_test_feeder_connection',
        # 后续扩展：
        # 'camera': '_test_camera_connection',
        # 'sensor': '_test_sensor_connection',
    }
    
    @classmethod
    def get_supported_categories(cls) -> List[str]:
        """获取支持连接测试的设备类别列表"""
        return list(cls.TESTER_MAP.keys())
    
    @classmethod
    def test_connection(cls, category: str, connection_info: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        """
        统一的设备连接测试入口
        
        Args:
            category: 设备类别（feeder, camera, sensor等）
            connection_info: 设备连接信息（不同设备类型字段不同）
            timeout: 超时时间（秒），默认15秒
            
        Returns:
            测试结果字典：
            {
                "success": bool,
                "message": str,
                "details": dict  # 设备特定的返回信息
            }
        """
        # 检查是否支持该设备类别
        if category not in cls.TESTER_MAP:
            supported = ', '.join(cls.TESTER_MAP.keys())
            return {
                "success": False,
                "message": f"❌ 不支持的设备类别: {category}",
                "details": {
                    "error": f"当前支持的设备类别: {supported}",
                    "category": category
                }
            }
        
        # 获取对应的测试方法并执行
        tester_method = getattr(cls, cls.TESTER_MAP[category])
        try:
            return tester_method(connection_info, timeout)
        except Exception as e:
            logger.error(f"设备连接测试异常 [{category}]: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": "❌ 测试过程发生异常",
                "details": {"error": str(e)}
            }
    
    @classmethod
    def _test_feeder_connection(cls, connection_info: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """
        喂食机连接测试
        
        connection_info 必需字段：
            - base_url: API地址，如: https://ffish.huaeran.cn:8081/commonRequest
            - user_id: 用户名
            - password: 密码
            
        Args:
            connection_info: 连接信息
            timeout: 超时时间（秒）
            
        Returns:
            测试结果字典
        """
        import requests
        
        # 验证必需字段
        required_fields = ['base_url', 'user_id', 'password']
        missing_fields = [f for f in required_fields if not connection_info.get(f)]
        if missing_fields:
            return {
                "success": False,
                "message": f"❌ 缺少必需字段: {', '.join(missing_fields)}",
                "details": {
                    "error": "connection_info 格式错误",
                    "required_fields": required_fields,
                    "missing_fields": missing_fields
                }
            }
        
        base_url = connection_info['base_url']
        user_id = connection_info['user_id']
        password = connection_info['password']
        
        try:
            # 构建登录请求
            payload = {
                "msgType": 1000,
                "userID": user_id,
                "password": password,
            }
            
            logger.info(f"测试喂食机连接: {base_url}, 用户: {user_id}")
            
            # 发送POST请求
            resp = requests.post(
                base_url,
                json=payload,
                verify=True,
                timeout=timeout
            )
            
            # 检查HTTP状态
            resp.raise_for_status()
            data = resp.json()
            
            # 检查登录状态
            status = data.get("status")
            if status == 1:
                authkey = data.get("data", [{}])[0].get("authkey", "")
                logger.info(f"喂食机连接测试成功: {base_url}")
                return {
                    "success": True,
                    "message": "✅ 连接测试成功，设备可以正常连接",
                    "details": {
                        "authkey": authkey[:10] + "..." if authkey and len(authkey) > 10 else authkey,
                        "response_status": status
                    }
                }
            else:
                error_msg = data.get("msg") or data.get("message") or "未知错误"
                logger.warning(f"喂食机连接测试失败: {base_url}, status={status}, error={error_msg}")
                return {
                    "success": False,
                    "message": f"❌ 连接测试失败: status={status}",
                    "details": {
                        "error": error_msg,
                        "response_status": status
                    }
                }
                
        except requests.exceptions.Timeout:
            logger.warning(f"喂食机连接超时: {base_url}, timeout={timeout}s")
            return {
                "success": False,
                "message": "❌ 连接超时",
                "details": {
                    "error": f"请求在 {timeout} 秒内未响应",
                    "timeout": timeout
                }
            }
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"喂食机连接错误: {base_url}, error={str(e)}")
            return {
                "success": False,
                "message": "❌ 无法连接到服务器",
                "details": {
                    "error": f"连接错误: {str(e)}"
                }
            }
        except requests.exceptions.RequestException as e:
            logger.warning(f"喂食机请求失败: {base_url}, error={str(e)}")
            return {
                "success": False,
                "message": "❌ 请求失败",
                "details": {
                    "error": str(e)
                }
            }
    
    # ==================== 后续扩展示例 ====================
    # @classmethod
    # def _test_camera_connection(cls, connection_info: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    #     """
    #     摄像头连接测试
    #     
    #     connection_info 必需字段：
    #         - rtsp_url: RTSP流地址，或
    #         - http_url: HTTP截图地址
    #         - username: 用户名（可选）
    #         - password: 密码（可选）
    #     """
    #     # TODO: 实现摄像头连接测试逻辑
    #     pass
