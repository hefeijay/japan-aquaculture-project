#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本陆上养殖生产管理AI助手服务端
提供AI决策消息的API接口服务
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import time
import math
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置日志
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI消息类型配置
MESSAGE_TYPES = [
    {"type": "analysis", "icon": "🔍", "color": "#00a8cc"},
    {"type": "warning", "icon": "⚠️", "color": "#ff6b35"},
    {"type": "action", "icon": "🎯", "color": "#20B2AA"},
    {"type": "optimization", "icon": "⚡", "color": "#41b3d3"}
]

# AI决策消息模板数据
AI_MESSAGES_POOL = [
    {"type": "analysis", "text": "检测到1号池塘pH值轻微下降，建议监控", "action": "持续观察pH变化趋势"},
    {"type": "warning", "text": "3号池塘溶解氧浓度接近临界值", "action": "启动增氧设备"},
    {"type": "action", "text": "基于历史数据，调整投食量至最优配比", "action": "投食量减少15%"},
    {"type": "optimization", "text": "水质参数稳定，建议维持当前管理策略", "action": "保持现状"},
    {"type": "analysis", "text": "温度传感器显示昼夜温差适宜鱼类生长", "action": "无需调整"},
    {"type": "warning", "text": "检测到2号池塘水位下降", "action": "检查进水阀门"},
    {"type": "action", "text": "AI模型预测未来6小时天气变化", "action": "准备应对降温措施"},
    {"type": "optimization", "text": "能耗优化：夜间模式已自动启动", "action": "设备功率降低30%"},
    {"type": "analysis", "text": "水质监测显示氨氮含量正常", "action": "继续定期检测"},
    {"type": "warning", "text": "4号池塘水温异常升高", "action": "启动降温系统"},
    {"type": "action", "text": "智能投食系统已调整投食时间", "action": "优化投食效率"},
    {"type": "optimization", "text": "循环水系统运行效率提升8%", "action": "保持当前配置"},
    {"type": "analysis", "text": "鱼类活动模式分析完成", "action": "调整监控策略"},
    {"type": "warning", "text": "备用电源电量不足", "action": "及时充电或更换"},
    {"type": "action", "text": "根据天气预报调整养殖计划", "action": "准备防护措施"}
]

def random_choice(items):
    """随机选择列表中的一个元素"""
    return random.choice(items)

def generate_message_id():
    """生成唯一的消息ID"""
    return f"msg_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

def format_japanese_time():
    """格式化为日本时间格式"""
    return datetime.now().strftime("%H:%M:%S")

@app.route('/api/ai/decisions/recent', methods=['GET'])
def get_ai_decisions():
    """
    获取AI决策消息接口
    返回格式：{ id: string, timestamp: number, type: string, message: string, action?: string }
    """
    try:
        # 随机返回1-2条新消息
        num_messages = 2 if random.random() > 0.7 else 1
        selected_messages = []
        
        for i in range(num_messages):
            # 随机选择一条消息
            message_data = random_choice(AI_MESSAGES_POOL)
            message_type = next((mt for mt in MESSAGE_TYPES if mt["type"] == message_data["type"]), MESSAGE_TYPES[0])
            
            # 构建消息对象
            message = {
                "id": generate_message_id(),
                "timestamp": int(time.time() * 1000) - (i * 30000),  # 30秒间隔
                "type": message_data["type"],
                "icon": message_type["icon"],
                "color": message_type["color"],
                "message": message_data["text"],
                "action": message_data["action"],
                "time": format_japanese_time()
            }
            
            selected_messages.append(message)
        
        # 返回JSON响应
        response = {
            "success": True,
            "data": selected_messages,
            "timestamp": int(time.time() * 1000),
            "count": len(selected_messages)
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        # 错误处理
        error_response = {
            "success": False,
            "error": str(e),
            "timestamp": int(time.time() * 1000)
        }
        return jsonify(error_response), 500

# 传感器数据生成函数
def generate_sensor_data_for_type(sensor_id, sensor_config):
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

@app.route('/api/sensors/realtime', methods=['GET'])
def get_sensor_data():
    """
    获取所有传感器的实时数据
    
    Returns:
        JSON格式的传感器数据，包含所有传感器类型的历史数据点
    """
    try:
        # 传感器类型配置（与前端保持一致）
        sensor_types = [
            {"id": "temperature", "name": "水温", "unit": "°C", "threshold": [18, 28]},
            {"id": "ph", "name": "pH值", "unit": "pH", "threshold": [6.5, 8.5]},
            {"id": "oxygen", "name": "溶解氧", "unit": "mg/L", "threshold": [5, 12]},
            {"id": "ammonia", "name": "氨氮", "unit": "mg/L", "threshold": [0, 0.5]},
            {"id": "nitrite", "name": "亚硝酸盐", "unit": "mg/L", "threshold": [0, 0.1]},
            {"id": "light", "name": "光照强度", "unit": "lux", "threshold": [1000, 5000]},
            {"id": "level", "name": "水位", "unit": "m", "threshold": [1.5, 3.0]},
            {"id": "flow", "name": "流量", "unit": "L/min", "threshold": [50, 200]}
        ]
        
        # 生成所有传感器数据
        sensor_data = {}
        for sensor in sensor_types:
            sensor_data[sensor["id"]] = generate_sensor_data_for_type(sensor["id"], sensor)
        
        logger.info(f"传感器数据请求成功，返回{len(sensor_types)}个传感器的数据")
        
        return jsonify({
            "success": True,
            "data": sensor_data,
            "timestamp": datetime.now().isoformat(),
            "sensor_count": len(sensor_types)
        })
        
    except Exception as e:
        logger.error(f"传感器数据生成失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/devices/status', methods=['GET'])
def get_device_status():
    """
    获取所有设备的状态信息
    
    Returns:
        JSON格式的设备状态数据，包含设备名称、状态、参数等信息
    """
    try:
        # 设备配置数据
        devices_config = [
            {"name": "增氧泵-1号池", "type": "aerator", "normalParams": {"power": 85, "flow": 120}},
            {"name": "增氧泵-2号池", "type": "aerator", "normalParams": {"power": 78, "flow": 115}},
            {"name": "过滤系统-主干", "type": "filter", "normalParams": {"pressure": 2.3, "efficiency": 94}},
            {"name": "投食机-A区", "type": "feeder", "normalParams": {"schedule": "正常", "remaining": 78}},
            {"name": "投食机-B区", "type": "feeder", "normalParams": {"schedule": "正常", "remaining": 65}},
            {"name": "循环水泵-1", "type": "pump", "normalParams": {"flow": 145, "temperature": 45}},
            {"name": "循环水泵-2", "type": "pump", "normalParams": {"flow": 138, "temperature": 43}},
            {"name": "紫外消毒器", "type": "sterilizer", "normalParams": {"intensity": 92, "runtime": 18}},
            {"name": "备用发电机", "type": "generator", "normalParams": {"fuel": 85, "readiness": 100}},
            {"name": "环境监控主机", "type": "monitor", "normalParams": {"sensors": 24, "connectivity": 98}}
        ]
        
        # 设备状态选项
        statuses = ["运行中", "待机", "维护中", "故障"]
        status_colors = {
            "运行中": "#20B2AA",
            "待机": "#41b3d3", 
            "维护中": "#ffa500",
            "故障": "#ff6b35"
        }
        
        # 生成设备状态数据
        devices_data = []
        for device in devices_config:
            # 大部分设备正常运行，少数设备可能有其他状态
            status = random_choice(statuses if random.random() > 0.85 else ["运行中"])
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
                "statusColor": status_colors[status],
                "parameters": parameters,
                "lastUpdate": last_update,
                "lastUpdateTime": datetime.fromtimestamp(last_update / 1000).strftime("%H:%M:%S")
            }
            
            devices_data.append(device_data)
        
        logger.info(f"设备状态数据请求成功，返回{len(devices_data)}个设备的状态")
        
        return jsonify({
            "success": True,
            "data": devices_data,
            "timestamp": datetime.now().isoformat(),
            "device_count": len(devices_data)
        })
        
    except Exception as e:
        logger.error(f"设备状态数据生成失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/location/data', methods=['GET'])
def get_location_data():
    """
    获取地理位置数据接口
    
    Returns:
        JSON格式的地理位置数据，包含养殖场各区域的位置信息
    """
    try:
        # 地理位置数据配置
        location_data = [
            {
                "id": "pond_1",
                "name": "1号养殖池",
                "type": "pond",
                "coordinates": {"lat": 35.6762, "lng": 139.6503},
                "area": 2500,  # 平方米
                "depth": 2.5,  # 米
                "capacity": 15000,  # 升
                "status": "active",
                "temperature": 22.5 + random.uniform(-2, 2),
                "ph": 7.2 + random.uniform(-0.3, 0.3),
                "oxygen": 8.5 + random.uniform(-1, 1)
            },
            {
                "id": "pond_2", 
                "name": "2号养殖池",
                "type": "pond",
                "coordinates": {"lat": 35.6765, "lng": 139.6508},
                "area": 3000,
                "depth": 3.0,
                "capacity": 18000,
                "status": "active",
                "temperature": 23.1 + random.uniform(-2, 2),
                "ph": 7.1 + random.uniform(-0.3, 0.3),
                "oxygen": 8.2 + random.uniform(-1, 1)
            },
            {
                "id": "pond_3",
                "name": "3号养殖池", 
                "type": "pond",
                "coordinates": {"lat": 35.6768, "lng": 139.6505},
                "area": 2800,
                "depth": 2.8,
                "capacity": 16500,
                "status": "maintenance",
                "temperature": 21.8 + random.uniform(-2, 2),
                "ph": 7.0 + random.uniform(-0.3, 0.3),
                "oxygen": 7.8 + random.uniform(-1, 1)
            },
            {
                "id": "control_center",
                "name": "控制中心",
                "type": "facility",
                "coordinates": {"lat": 35.6760, "lng": 139.6500},
                "area": 200,
                "status": "operational",
                "equipment_count": 24,
                "connectivity": 98 + random.uniform(-5, 2)
            },
            {
                "id": "processing_plant",
                "name": "加工厂房",
                "type": "facility", 
                "coordinates": {"lat": 35.6770, "lng": 139.6510},
                "area": 800,
                "status": "operational",
                "capacity": 500,  # kg/day
                "efficiency": 85 + random.uniform(-10, 10)
            },
            {
                "id": "storage_area",
                "name": "储存区域",
                "type": "facility",
                "coordinates": {"lat": 35.6758, "lng": 139.6495},
                "area": 300,
                "status": "operational",
                "temperature": 4.2 + random.uniform(-1, 1),
                "humidity": 65 + random.uniform(-10, 10)
            }
        ]
        
        # 添加时间戳和随机变化
        for location in location_data:
            location["lastUpdate"] = int(time.time() * 1000) - random.randint(1000, 180000)
            location["lastUpdateTime"] = datetime.fromtimestamp(location["lastUpdate"] / 1000).strftime("%H:%M:%S")
        
        logger.info(f"地理位置数据请求成功，返回{len(location_data)}个位置的数据")
        
        return jsonify({
            "success": True,
            "data": location_data,
            "timestamp": datetime.now().isoformat(),
            "location_count": len(location_data)
        })
        
    except Exception as e:
        logger.error(f"地理位置数据生成失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/cameras/<int:camera_id>/status', methods=['GET'])
def get_camera_status(camera_id):
    """
    获取摄像头状态数据接口
    
    Args:
        camera_id: 摄像头ID
        
    Returns:
        JSON格式的摄像头状态数据
    """
    try:
        # 摄像头位置配置
        locations = [
            '主养殖区东北角',
            '投食区中心位置', 
            '过滤设备附近',
            '南侧水体监控',
            '应急备用区域',
            '北侧深水区',
            '中央监控点',
            '西侧浅水区'
        ]
        
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
            "location": locations[(camera_id - 1) % len(locations)],
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
        
        logger.info(f"摄像头{camera_id}状态请求成功，状态: {status}")
        
        return jsonify({
            "success": True,
            "data": camera_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"摄像头{camera_id}状态获取失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "AI Assistant API",
        "timestamp": int(time.time() * 1000)
    }), 200

@app.route('/', methods=['GET'])
def index():
    """根路径信息"""
    return jsonify({
        "service": "日本陆上养殖生产管理AI助手API",
        "version": "1.0.0",
        "endpoints": {
            "ai_decisions": "/api/ai/decisions/recent",
            "sensors_realtime": "/api/sensors/realtime",
            "devices_status": "/api/devices/status",
            "location_data": "/api/location/data",
            "camera_status": "/api/cameras/{id}/status",
            "health": "/api/health"
        },
        "timestamp": int(time.time() * 1000)
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 日本陆上养殖生产管理AI助手服务端启动中...")
    print("📡 API地址: http://127.0.0.1:5002")
    print("🔗 AI决策接口: http://127.0.0.1:5002/api/ai/decisions/recent")
    print("🌡️ 传感器数据接口: http://127.0.0.1:5002/api/sensors/realtime")
    print("🔧 设备状态接口: http://127.0.0.1:5002/api/devices/status")
    print("📍 地理位置接口: http://127.0.0.1:5002/api/location/data")
    print("📹 摄像头状态接口: http://127.0.0.1:5002/api/cameras/{id}/status")
    print("💚 健康检查: http://127.0.0.1:5002/api/health")
    print("=" * 60)
    
    # 启动Flask服务器
    app.run(
        host='0.0.0.0',  # 监听所有网络接口
        port=5002,       # 端口5002
        debug=True,      # 开发模式
        threaded=True    # 多线程支持
    )