#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证工具模块
提供认证装饰器和相关功能
"""

from functools import wraps
from flask import jsonify, request
import logging

logger = logging.getLogger(__name__)


def auth_required(fn):
    """
    认证装饰器
    验证JWT Token并提取用户信息
    
    注意：如果项目未配置JWT，此装饰器将跳过认证
    可以通过环境变量 ENABLE_AUTH 控制是否启用认证
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # 检查是否启用认证
            import os
            enable_auth = os.getenv('ENABLE_AUTH', 'false').lower() in ('true', '1', 'yes')
            
            if not enable_auth:
                # 未启用认证，使用默认值
                user_id = request.headers.get('X-User-Id', 'default_user')
                role = request.headers.get('X-User-Role', 'user')
                return fn(user_id=user_id, role=role, *args, **kwargs)
            
            # 如果启用了认证，尝试使用 JWT
            try:
                from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
                
                # 验证JWT Token
                verify_jwt_in_request()
                
                # 提取身份和角色信息
                user_id = get_jwt_identity()
                claims = get_jwt()
                role = claims.get("role", "user")
                
                if not user_id:
                    return jsonify({
                        "code": 401,
                        "msg": "未授权：缺少用户身份信息",
                        "data": {}
                    }), 401
                
                return fn(user_id=user_id, role=role, *args, **kwargs)
                
            except ImportError:
                logger.warning("flask_jwt_extended 未安装，跳过JWT认证")
                # 回退到简单的header认证
                user_id = request.headers.get('X-User-Id', 'default_user')
                role = request.headers.get('X-User-Role', 'user')
                return fn(user_id=user_id, role=role, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"JWT认证失败: {str(e)}")
                return jsonify({
                    "code": 401,
                    "msg": f"认证失败: {str(e)}",
                    "data": {}
                }), 401
                
        except Exception as e:
            logger.error(f"认证装饰器错误: {str(e)}", exc_info=True)
            return jsonify({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": {}
            }), 500
    
    return wrapper

