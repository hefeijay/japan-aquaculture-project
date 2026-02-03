#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask应用工厂
负责创建和配置Flask应用实例
"""

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
import logging
import sys
import os
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from config.settings import Config
from routes.api_routes import api_bp
from routes.main_routes import main_bp

# 导入数据库模型（统一包路径，避免产生多个 SQLAlchemy 实例）
from db_models import db


class UnicodeJSONProvider(DefaultJSONProvider):
    """
    自定义JSON提供器，确保中文字符不被转义为Unicode序列
    """
    def dumps(self, obj, **kwargs):
        """重写dumps方法，确保ensure_ascii=False"""
        kwargs.setdefault('ensure_ascii', False)
        return json.dumps(obj, **kwargs)


def create_app(config_class=Config):
    """
    创建Flask应用实例
    
    Args:
        config_class: 配置类，默认使用Config
        
    Returns:
        配置好的Flask应用实例
    """
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config_class)
    
    # 配置JSON编码器：使用自定义JSONProvider确保中文字符直接显示，不转义为Unicode
    app.json = UnicodeJSONProvider(app)
    
    # 添加数据库配置（统一使用 Config，可通过环境变量覆盖）
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化数据库
    db.init_app(app)
    
    # 配置CORS
    CORS(app)  # 允许跨域请求
    
    # 配置JWT（如果启用了认证）
    enable_auth = os.getenv('ENABLE_AUTH', 'false').lower() in ('true', '1', 'yes')
    if enable_auth:
        try:
            from flask_jwt_extended import JWTManager
            from datetime import timedelta
            
            # JWT配置
            jwt_secret_key = os.getenv('JWT_SECRET_KEY', 'change-this-secret-key-in-production')
            app.config['JWT_SECRET_KEY'] = jwt_secret_key
            app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)  # token过期时间，24小时
            app.config['JWT_TOKEN_LOCATION'] = ['headers']  # 从请求头获取token
            app.config['JWT_HEADER_NAME'] = 'Authorization'  # 请求头名称
            app.config['JWT_HEADER_TYPE'] = 'Bearer'  # token类型
            
            # 初始化JWT
            jwt = JWTManager(app)
            logger = logging.getLogger(__name__)
            logger.info("JWT认证已启用")
        except ImportError:
            logger = logging.getLogger(__name__)
            logger.warning("flask_jwt_extended 未安装，JWT认证未启用")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"JWT初始化失败: {str(e)}", exc_info=True)
    
    # 配置日志
    logging.basicConfig(level=getattr(logging, config_class.LOG_LEVEL))
    logger = logging.getLogger(__name__)
    logger.info("Flask应用初始化完成")
    
    # 注册蓝图
    from routes.ai_decision_routes import ai_decision_bp
    from routes.message_queue_routes import message_queue_bp
    from routes.data_collection_routes import data_collection_bp
    from routes.file_upload_routes import file_upload_bp
    from routes.alert_routes import alert_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_decision_bp)
    app.register_blueprint(message_queue_bp)
    app.register_blueprint(data_collection_bp)
    app.register_blueprint(file_upload_bp)
    app.register_blueprint(alert_bp)
    
    logger.info("所有蓝图注册完成")
    
    return app


def print_startup_info():
    """
    打印启动信息
    """
    print("=" * 60)
    print("🤖 日本陆上养殖生产管理AI助手服务端启动中...")
    print(f"📡 API地址: http://localhost:{Config.PORT}")
    print(f"🔗 AI决策接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['ai_decisions']}")
    print(f"🌡️ 传感器数据接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['sensors_realtime']}")
    print(f"🔧 设备状态接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['devices_status']}")
    print(f"📍 地理位置接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['location_data']}")
    print(f"📹 摄像头状态接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['camera_status']}")
    print(f"📸 摄像头图片接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['camera_image']}")
    print(f"🏥 摄像头健康检查: http://localhost:{Config.PORT}{Config.ENDPOINTS['camera_health']}")
    print(f"💚 健康检查: http://localhost:{Config.PORT}{Config.ENDPOINTS['health']}")
    print(f"📤 文件上传接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['file_upload']}")
    print(f"📤 多文件上传接口: http://localhost:{Config.PORT}{Config.ENDPOINTS['file_upload_multiple']}")
    if Config.FILE_FORWARD_URL and Config.FILE_FORWARD_URL.lower() != 'none':
        print(f"🔄 文件转发地址: {Config.FILE_FORWARD_URL}")
    else:
        print(f"🔄 文件转发: 未启用（FILE_FORWARD_URL=none）")
    print("=" * 60)