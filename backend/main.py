#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本陆上养殖生产管理AI助手服务端主入口
使用模块化架构重构的新版本
"""

from app_factory import create_app, print_startup_info
from config.settings import Config 
from services.aggregator_service import aggregator_service


def main():
    """
    主函数：创建并启动Flask应用
    """
    # 打印启动信息
    # print_startup_info()
    
    # 创建应用实例
    app = create_app()

    # 启动周期聚合服务（后台线程）
    try:
        aggregator_service.start()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"启动聚合服务失败: {e}")
    
    # 启动Flask服务器
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        threaded=Config.THREADED
    )


if __name__ == '__main__':
    main()