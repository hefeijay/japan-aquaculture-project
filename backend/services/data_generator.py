#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据生成服务模块
负责生成各种模拟数据，包括传感器数据、设备状态、地理位置数据等
"""

import random
import time
import math
from datetime import datetime
from typing import List, Dict, Any

from ..config.settings import (
    AI_MESSAGES_POOL, MESSAGE_TYPES, SENSOR_TYPES, DEVICES_CONFIG,
    DEVICE_STATUSES, DEVICE_STATUS_COLORS, LOCATION_DATA, CAMERA_LOCATIONS
)

# 导入传感器服务
try:
    from .sensor_service import SensorService
    SENSOR_SERVICE_AVAILABLE = True
except ImportError:
    SENSOR_SERVICE_AVAILABLE = False
    print("Warning: SensorService not available, using simulated data only")


class DataGeneratorService:
    """数据生成服务类"""
    
    @staticmethod
    def random_choice(items: List[Any]) -> Any:
        """
        随机选择列表中的一个元素
        
        Args:
            items: 待选择的列表
            
        Returns:
            随机选中的元素
        """
        return random.choice(items)
    
    @staticmethod
    def generate_message_id() -> str:
        """
        生成唯一的消息ID
        
        Returns:
            格式化的消息ID字符串
        """
        return f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    
    @staticmethod
    def format_japanese_time() -> str:
        """
        格式化为日本时间格式
        
        Returns:
            日本时间格式的字符串
        """
        return datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

    @classmethod
    def generate_ai_decisions(cls, num_messages: int = None) -> List[Dict[str, Any]]:
        """
        生成AI决策消息（基于数据库）
        
        Args:
            num_messages: 消息数量，如果为None则获取所有活跃消息
            
        Returns:
            AI决策消息列表
        """
        try:
            # 导入AI决策服务
            from japan_server.services.ai_decision_service import AIDecisionService
            
            # 从数据库获取决策消息
            decisions = AIDecisionService.get_recent_decisions(
                num_messages=num_messages,
                max_age_hours=24  # 获取24小时内的消息
            )
            
            # 如果数据库中没有消息，则使用原有的随机生成逻辑作为后备
            if not decisions:
                print("数据库中没有AI决策消息，使用后备方案")
                return cls._generate_fallback_decisions(num_messages)
            
            return decisions
            
        except Exception as e:
            print(f"从数据库获取AI决策消息失败: {e}")
            # 发生错误时使用后备方案
            return cls._generate_fallback_decisions(num_messages)
    
    @classmethod
    def _generate_fallback_decisions(cls, num_messages: int = None) -> List[Dict[str, Any]]:
        """
        后备的AI决策消息生成方法（原有逻辑）
        
        Args:
            num_messages: 消息数量，默认随机1-2条
            
        Returns:
            AI决策消息列表
        """
        if num_messages is None:
            num_messages = 2 if random.random() > 0.7 else 1
            
        selected_messages = []
        
        for i in range(num_messages):
            # 随机选择一条消息
            message_data = cls.random_choice(AI_MESSAGES_POOL)
            message_type = next(
                (mt for mt in MESSAGE_TYPES if mt["type"] == message_data["type"]), 
                MESSAGE_TYPES[0]
            )
            
            # 构建消息对象
            message = {
                "id": cls.generate_message_id(),
                "timestamp": int(time.time() * 1000) - (i * 30000),  # 30秒间隔
                "type": message_data["type"],
                "icon": message_type["icon"],
                "color": message_type["color"],
                "message": message_data["text"],
                "action": message_data["action"],
                "time": cls.format_japanese_time()
            }
            
            selected_messages.append(message)
            
        return selected_messages
    
    @classmethod
    def generate_sensor_data_for_type(cls, sensor_id: str, sensor_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        为指定传感器类型生成实时数据
        
        Args:
            sensor_id: 传感器ID (temperature, ph, oxygen等)
            sensor_config: 传感器配置信息
        
        Returns:
            包含30个历史数据点的列表
        """
        now = int(time.time() * 1000)  # 毫秒时间戳
        points = []
        
        # 生成最近30个数据点（每个点间隔2分钟）
        for i in range(29, -1, -1):
            timestamp = now - (i * 2 * 60 * 1000)  # 2分钟间隔
            
            # 根据传感器类型生成合理的数据
            if sensor_id == 'temperature':
                value = 20 + random.uniform(0, 6) + math.sin(i * 0.1) * 2
            elif sensor_id == 'ph':
                value = 7.0 + random.uniform(0, 0.8) + math.sin(i * 0.15) * 0.3
            elif sensor_id == 'oxygen':
                value = 6 + random.uniform(0, 3) + math.sin(i * 0.2) * 1
            elif sensor_id == 'ammonia':
                value = 0.1 + random.uniform(0, 0.2) + math.sin(i * 0.05) * 0.1
            elif sensor_id == 'nitrite':
                value = 0.02 + random.uniform(0, 0.06) + math.sin(i * 0.1) * 0.02
            elif sensor_id == 'light':
                value = 2000 + random.uniform(0, 2000) + math.sin(i * 0.3) * 500
            elif sensor_id == 'level':
                value = 2.0 + random.uniform(0, 0.5) + math.sin(i * 0.05) * 0.2
            elif sensor_id == 'flow':
                value = 80 + random.uniform(0, 70) + math.sin(i * 0.1) * 20
            else:
                value = random.uniform(0, 100)
            
            # 确保值不为负数
            value = max(0, value)
            
            # 格式化时间
            time_str = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M')
            
            points.append({
                "timestamp": timestamp,
                "value": round(value, 2),
                "time": time_str
            })
        
        return points
    
    @classmethod
    def generate_all_sensor_data(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        生成所有传感器的实时数据
        优先从数据库获取真实数据，如果没有数据则使用模拟数据
        
        Returns:
            包含所有传感器数据的字典
        """
        # 尝试从数据库获取真实数据
        if SENSOR_SERVICE_AVAILABLE:
            try:
                # 检查数据库中是否有传感器读数数据
                if SensorService.has_sensor_data():
                    # 获取数据库中的传感器读数（最近1小时）
                    db_sensor_data = SensorService.get_all_sensor_readings(hours=1)
                    
                    # 如果数据库有数据，使用数据库数据
                    if db_sensor_data:
                        # 补充缺失的传感器类型（使用模拟数据）
                        sensor_data = db_sensor_data.copy()
                        
                        # 获取所有配置的传感器类型
                        configured_sensor_ids = {sensor["id"] for sensor in SENSOR_TYPES}
                        existing_sensor_ids = set(sensor_data.keys())
                        
                        # 为缺失的传感器类型生成模拟数据
                        missing_sensor_ids = configured_sensor_ids - existing_sensor_ids
                        for sensor in SENSOR_TYPES:
                            if sensor["id"] in missing_sensor_ids:
                                sensor_data[sensor["id"]] = cls.generate_sensor_data_for_type(sensor["id"], sensor)
                        
                        return sensor_data
            except Exception as e:
                print(f"从数据库获取传感器数据失败，使用模拟数据: {str(e)}")
        
        # 回退到模拟数据生成
        sensor_data = {}
        for sensor in SENSOR_TYPES:
            sensor_data[sensor["id"]] = cls.generate_sensor_data_for_type(sensor["id"], sensor)
        
        return sensor_data
    
    @classmethod
    def generate_device_status_data(cls) -> List[Dict[str, Any]]:
        """
        生成所有设备的状态信息
        
        Returns:
            设备状态数据列表
        """
        devices_data = []
        
        for device in DEVICES_CONFIG:
            # 大部分设备正常运行，少数设备可能有其他状态
            status = cls.random_choice(DEVICE_STATUSES if random.random() > 0.85 else ["运行中"])
            last_update = int(time.time() * 1000) - random.randint(1000, 300000)  # 最近5分钟内更新
            
            # 根据状态调整参数
            parameters = device["normalParams"].copy()
            if status == "故障":
                # 故障状态下参数降低
                for key, value in parameters.items():
                    if isinstance(value, (int, float)):
                        parameters[key] = max(0, value * random.uniform(0.3, 0.7))
            elif status == "维护中":
                # 维护状态下添加进度信息
                parameters["maintenanceProgress"] = f"{random.randint(30, 95)}%"
            
            device_data = {
                "id": f"device_{device['name'].replace('-', '_').replace('号', '').replace('区', '')}",
                "name": device["name"],
                "type": device["type"],
                "status": status,
                "statusColor": DEVICE_STATUS_COLORS[status],
                "parameters": parameters,
                "lastUpdate": last_update,
                "lastUpdateTime": datetime.fromtimestamp(last_update / 1000).strftime("%H:%M:%S")
            }
            
            devices_data.append(device_data)
        
        return devices_data
    
    @classmethod
    def generate_location_data(cls) -> List[Dict[str, Any]]:
        """
        生成地理位置数据
        
        Returns:
            地理位置数据列表
        """
        location_data = []
        
        for location in LOCATION_DATA:
            location_copy = location.copy()
            
            # 为池塘添加实时水质数据
            if location_copy["type"] == "pond":
                location_copy.update({
                    "temperature": 22.5 + random.uniform(-2, 2),
                    "ph": 7.2 + random.uniform(-0.3, 0.3),
                    "oxygen": 8.5 + random.uniform(-1, 1)
                })
            
            # 为控制中心添加连接性数据
            elif location_copy["id"] == "control_center":
                location_copy["connectivity"] = 98 + random.uniform(-5, 2)
            
            # 为加工厂房添加效率数据
            elif location_copy["id"] == "processing_plant":
                location_copy["efficiency"] = 85 + random.uniform(-10, 10)
            
            # 为储存区域添加环境数据
            elif location_copy["id"] == "storage_area":
                location_copy.update({
                    "temperature": 4.2 + random.uniform(-1, 1),
                    "humidity": 65 + random.uniform(-10, 10)
                })
            
            # 添加时间戳
            location_copy["lastUpdate"] = int(time.time() * 1000) - random.randint(1000, 180000)
            location_copy["lastUpdateTime"] = datetime.fromtimestamp(
                location_copy["lastUpdate"] / 1000
            ).strftime("%H:%M:%S")
            
            location_data.append(location_copy)
        
        return location_data
    
    @classmethod
    def generate_camera_status(cls, camera_id: int) -> Dict[str, Any]:
        """
        生成摄像头状态数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头状态数据字典
        """
        # 模拟摄像头状态（90%在线率）
        is_online = random.random() > 0.1
        status = '在线' if is_online else '离线'
        
        # 模拟画质（80%高质量）
        quality_rand = random.random()
        if quality_rand > 0.8:
            quality = '低'
        elif quality_rand > 0.5:
            quality = '中'
        else:
            quality = '高'
        
        camera_data = {
            "id": camera_id,
            "name": f"监控摄像头-{camera_id}",
            "location": CAMERA_LOCATIONS[(camera_id - 1) % len(CAMERA_LOCATIONS)],
            "status": status,
            "quality": quality,
            "resolution": "1920x1080",
            "fps": random.randint(10, 30) if is_online else 0,
            "lastUpdate": int(time.time() * 1000),
            "lastUpdateTime": datetime.now().strftime("%H:%M:%S"),
            "temperature": 22.0 + random.uniform(-3, 3) if is_online else None,
            "connectivity": random.randint(85, 100) if is_online else 0,
            "recording": is_online and random.random() > 0.2,
            "nightVision": random.random() > 0.5,
            "motionDetection": is_online and random.random() > 0.3
        }
        
        return camera_data

    @classmethod
    def generate_camera_image(cls, camera_id: int) -> Dict[str, Any]:
        """
        生成摄像头图片数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头图片数据字典
        """
        # 模拟摄像头状态
        is_online = random.random() > 0.1
        
        if not is_online:
            return {
                "id": camera_id,
                "name": f"监控摄像头-{camera_id}",
                "location": CAMERA_LOCATIONS[(camera_id - 1) % len(CAMERA_LOCATIONS)],
                "status": "离线",
                "image_url": None,
                "error": "摄像头离线，无法获取图片",
                "timestamp": int(time.time() * 1000)
            }
        
        # 模拟图片URL（实际应用中应该是真实的图片URL或base64数据）
        image_urls = [
            f"https://example.com/camera/{camera_id}/image_{int(time.time())}.jpg",
            f"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
        ]
        
        image_data = {
            "id": camera_id,
            "name": f"监控摄像头-{camera_id}",
            "location": CAMERA_LOCATIONS[(camera_id - 1) % len(CAMERA_LOCATIONS)],
            "status": "在线",
            "image_url": random.choice(image_urls),
            "resolution": "1920x1080",
            "format": "JPEG",
            "size_kb": random.randint(150, 800),
            "timestamp": int(time.time() * 1000),
            "capture_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": {
                "brightness": random.randint(40, 90),
                "contrast": random.randint(50, 100),
                "saturation": random.randint(60, 100),
                "exposure": random.uniform(0.5, 2.0)
            }
        }
        
        return image_data

    @classmethod
    def generate_camera_health(cls, camera_id: int) -> Dict[str, Any]:
        """
        生成摄像头健康状态数据
        
        Args:
            camera_id: 摄像头ID
            
        Returns:
            摄像头健康状态数据字典
        """
        # 模拟摄像头在线状态
        is_online = random.random() > 0.1
        
        if not is_online:
            return {
                "id": camera_id,
                "name": f"监控摄像头-{camera_id}",
                "location": CAMERA_LOCATIONS[(camera_id - 1) % len(CAMERA_LOCATIONS)],
                "health_status": "离线",
                "overall_score": 0,
                "checks": {
                    "connectivity": {"status": "失败", "score": 0, "message": "无法连接到摄像头"},
                    "image_quality": {"status": "未知", "score": 0, "message": "摄像头离线"},
                    "hardware": {"status": "未知", "score": 0, "message": "无法检测硬件状态"},
                    "storage": {"status": "未知", "score": 0, "message": "无法检测存储状态"}
                },
                "timestamp": int(time.time() * 1000),
                "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # 生成各项健康检查结果
        connectivity_score = random.randint(85, 100)
        image_quality_score = random.randint(70, 95)
        hardware_score = random.randint(80, 100)
        storage_score = random.randint(60, 95)
        
        # 计算总体健康分数
        overall_score = (connectivity_score + image_quality_score + hardware_score + storage_score) / 4
        
        # 确定健康状态
        if overall_score >= 90:
            health_status = "优秀"
        elif overall_score >= 75:
            health_status = "良好"
        elif overall_score >= 60:
            health_status = "一般"
        else:
            health_status = "需要维护"
        
        health_data = {
            "id": camera_id,
            "name": f"监控摄像头-{camera_id}",
            "location": CAMERA_LOCATIONS[(camera_id - 1) % len(CAMERA_LOCATIONS)],
            "health_status": health_status,
            "overall_score": round(overall_score, 1),
            "checks": {
                "connectivity": {
                    "status": "正常" if connectivity_score >= 80 else "异常",
                    "score": connectivity_score,
                    "message": f"网络连接质量: {connectivity_score}%"
                },
                "image_quality": {
                    "status": "正常" if image_quality_score >= 70 else "异常",
                    "score": image_quality_score,
                    "message": f"图像质量评分: {image_quality_score}%"
                },
                "hardware": {
                    "status": "正常" if hardware_score >= 80 else "异常",
                    "score": hardware_score,
                    "message": f"硬件状态评分: {hardware_score}%"
                },
                "storage": {
                    "status": "正常" if storage_score >= 60 else "异常",
                    "score": storage_score,
                    "message": f"存储空间使用率: {100-storage_score}%"
                }
            },
            "temperature": 22.0 + random.uniform(-3, 3),
            "uptime_hours": random.randint(1, 720),  # 1小时到30天
            "timestamp": int(time.time() * 1000),
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return health_data