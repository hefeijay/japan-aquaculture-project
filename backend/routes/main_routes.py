#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主路由蓝图
包含根路径和基础信息路由
"""

from flask import Blueprint, jsonify
import time

from config.settings import Config

# 创建蓝图
main_bp = Blueprint('main', __name__)


@main_bp.route('/', methods=['GET'])
def index():
    """
    根路径信息接口
    
    Returns:
        服务基本信息和可用端点列表
    """
    return jsonify({
        "service": Config.SERVICE_NAME,
        "version": Config.VERSION,
        "endpoints": Config.ENDPOINTS,
        "timestamp": int(time.time() * 1000)
    }), 200