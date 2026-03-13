#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本陆上养殖生产管理AI助手配置文件
包含所有系统配置、消息类型、传感器配置等
"""
import os

# 兼容 external_data_server：在模块导入阶段加载 .env
# 优先使用 python-dotenv；若不可用，回退到简易解析
try:
    from dotenv import load_dotenv  # type: ignore
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
    if os.path.exists(_ENV_PATH):
        load_dotenv(_ENV_PATH, override=False)  # 不覆盖已存在的环境变量
    else:
        # 允许从当前工作目录回退加载（开发时常用）
        load_dotenv(override=False)
except Exception:
    try:
        _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    # 仅在未设置时写入，避免覆盖已有变量
                    os.environ.setdefault(k.strip(), v)
    except Exception:
        # 安静失败，不影响后续 Config 的默认值
        pass

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

# 传感器类型配置
SENSOR_TYPES = [
    {"id": "temperature", "name": "水温", "unit": "°C", "threshold": [18, 28]},
    {"id": "ph", "name": "pH值", "unit": "pH", "threshold": [6.5, 8.5]},
    {"id": "oxygen", "name": "溶解氧", "unit": "mg/L", "threshold": [5, 12]},
    {"id": "turbidity", "name": "浊度", "unit": "NTU", "threshold": [0, 50]},
    {"id": "ammonia", "name": "氨氮", "unit": "mg/L", "threshold": [0, 0.5]},
    {"id": "nitrite", "name": "亚硝酸盐", "unit": "mg/L", "threshold": [0, 0.1]},
    {"id": "light", "name": "光照强度", "unit": "lux", "threshold": [1000, 5000]},
    {"id": "level", "name": "水位", "unit": "m", "threshold": [1.5, 3.0]},
    {"id": "flow", "name": "流量", "unit": "L/min", "threshold": [50, 200]}
]

# 设备配置数据
DEVICES_CONFIG = [
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

# 设备状态配置
DEVICE_STATUSES = ["运行中", "待机", "维护中", "故障"]
DEVICE_STATUS_COLORS = {
    "运行中": "#20B2AA",
    "待机": "#41b3d3", 
    "维护中": "#ffa500",
    "故障": "#ff6b35"
}

# 地理位置数据配置
LOCATION_DATA = [
    {
        "id": "pond_1",
        "name": "1号养殖池",
        "type": "pond",
        "coordinates": {"lat": 35.6762, "lng": 139.6503},
        "area": 2500,  # 平方米
        "depth": 2.5,  # 米
        "capacity": 15000,  # 升
        "status": "active"
    },
    {
        "id": "pond_2", 
        "name": "2号养殖池",
        "type": "pond",
        "coordinates": {"lat": 35.6765, "lng": 139.6508},
        "area": 3000,
        "depth": 3.0,
        "capacity": 18000,
        "status": "active"
    },
    {
        "id": "pond_3",
        "name": "3号养殖池", 
        "type": "pond",
        "coordinates": {"lat": 35.6768, "lng": 139.6505},
        "area": 2800,
        "depth": 2.8,
        "capacity": 16500,
        "status": "maintenance"
    },
    {
        "id": "control_center",
        "name": "控制中心",
        "type": "facility",
        "coordinates": {"lat": 35.6760, "lng": 139.6500},
        "area": 200,
        "status": "operational",
        "equipment_count": 24
    },
    {
        "id": "processing_plant",
        "name": "加工厂房",
        "type": "facility", 
        "coordinates": {"lat": 35.6770, "lng": 139.6510},
        "area": 800,
        "status": "operational",
        "capacity": 500  # kg/day
    },
    {
        "id": "storage_area",
        "name": "储存区域",
        "type": "facility",
        "coordinates": {"lat": 35.6758, "lng": 139.6495},
        "area": 300,
        "status": "operational"
    }
]

# 摄像头位置配置
CAMERA_LOCATIONS = [
    '主养殖区东北角',
    '投食区中心位置', 
    '过滤设备附近',
    '南侧水体监控',
    '应急备用区域',
    '北侧深水区',
    '中央监控点',
    '西侧浅水区'
]

# Flask应用配置
class Config:
    """Flask应用配置类"""
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5002'))
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')
    THREADED = True
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    
    # 数据库配置（支持环境变量覆盖）
    # 优先使用 MYSQL_* 环境变量拼接 URI；若未提供，则回退到 DATABASE_URL；再回退到默认值
    _MYSQL_HOST = os.getenv('MYSQL_HOST')
    _MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    _MYSQL_USER = os.getenv('MYSQL_USER')
    _MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    _MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

    _MYSQL_ENV_URI = None
    if all([_MYSQL_HOST, _MYSQL_USER, _MYSQL_PASSWORD, _MYSQL_DATABASE]):
        _MYSQL_ENV_URI = f"mysql+pymysql://{_MYSQL_USER}:{_MYSQL_PASSWORD}@{_MYSQL_HOST}:{_MYSQL_PORT}/{_MYSQL_DATABASE}"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        _MYSQL_ENV_URI
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API信息
    SERVICE_NAME = "日本陆上养殖生产管理AI助手API"
    VERSION = "1.0.0"
    
    # API接口端点配置
    ENDPOINTS = {
        "ai_decisions": "/api/ai/decisions/recent",
        "sensors_realtime": "/api/sensors/realtime",
        "devices_status": "/api/devices/status",
        "location_data": "/api/location/data",
        "camera_status": "/api/cameras/{id}/status",
        "camera_image": "/api/cameras/{id}/image",
        "camera_health": "/api/cameras/{id}/health",
        "health": "/api/health",
        "file_upload": "/api/upload",
        "file_upload_multiple": "/api/upload/multiple"
    }

    # 周期聚合任务配置（可通过环境变量覆盖）
    AGGREGATOR_INTERVAL_SECONDS = int(os.getenv('AGGREGATOR_INTERVAL_SECONDS', '3600'))
    AGGREGATOR_DEFAULT_WINDOW_MINUTES = int(os.getenv('AGGREGATOR_DEFAULT_WINDOW_MINUTES', '60'))
    AGGREGATOR_DEFAULT_POND_ID = os.getenv('AGGREGATOR_DEFAULT_POND_ID', '4')
    
    # 文件转发配置（可通过环境变量覆盖）
    FILE_FORWARD_URL = os.getenv('FILE_FORWARD_URL', 'http://8.216.33.92:5003/process_file')  # 默认转发到 8.216.33.92/process_file
    
    # 传感器实时数据配置（可通过环境变量覆盖）
    SENSOR_REALTIME_LIMIT = int(os.getenv('SENSOR_REALTIME_LIMIT', '24'))  # 每个 metric 获取的最新记录数，默认24条
    
    # ==================== SSE 实时推送配置 ====================
    # SSE 轮询间隔（秒），默认5秒
    SSE_POLL_INTERVAL = int(os.getenv('SSE_POLL_INTERVAL', '5'))
    
    # ==================== 时区配置 ====================
    # 本地时区偏移量（小时），默认为日本时区 UTC+9
    # 可通过环境变量 LOCAL_TIMEZONE_OFFSET 覆盖
    LOCAL_TIMEZONE_OFFSET = int(os.getenv('LOCAL_TIMEZONE_OFFSET', '9'))
    
    # ==================== 预警调度配置 ====================
    # 防抖时间（秒）：同一规则在此时间内不重复预警
    ALERT_DEBOUNCE_SECONDS = int(os.getenv('ALERT_DEBOUNCE_SECONDS', '300'))
    
    # APScheduler 配置
    # 同一任务最多并发实例数
    ALERT_SCHEDULER_MAX_INSTANCES = int(os.getenv('ALERT_SCHEDULER_MAX_INSTANCES', '1'))
    
    # 错过的任务是否合并执行
    ALERT_SCHEDULER_COALESCE = os.getenv('ALERT_SCHEDULER_COALESCE', 'true').lower() in ('1', 'true', 'yes')
    
    # 错过执行的宽限时间（秒）
    ALERT_SCHEDULER_MISFIRE_GRACE_TIME = int(os.getenv('ALERT_SCHEDULER_MISFIRE_GRACE_TIME', '60'))
    
    # 线程池大小：最多同时执行多少个不同规则的检查任务
    ALERT_SCHEDULER_THREAD_POOL_SIZE = int(os.getenv('ALERT_SCHEDULER_THREAD_POOL_SIZE', '10'))

    # ==================== 心跳 WebSocket 监控配置 ====================
    HEARTBEAT_WS_PORT = int(os.getenv('HEARTBEAT_WS_PORT', '12800'))
    HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv('HEARTBEAT_TIMEOUT_SECONDS', '300'))
    HEARTBEAT_CHECK_INTERVAL_SECONDS = int(os.getenv('HEARTBEAT_CHECK_INTERVAL_SECONDS', '30'))
    HEARTBEAT_ALERT_COOLDOWN_SECONDS = int(os.getenv('HEARTBEAT_ALERT_COOLDOWN_SECONDS', '3600'))

    # ==================== MQTT 设备控制配置 ====================
    MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', '')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    MQTT_USER = os.getenv('MQTT_USER', 'aqua_device')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')