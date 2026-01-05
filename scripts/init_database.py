#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
使用 create_app 中的 db 来初始化数据库表
"""

import sys
import os

# 添加 backend 目录到 Python 路径
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app_factory import create_app
from db_models import db


def init_database():
    """
    在应用上下文中创建所有数据库表。
    如果表已存在，则不会重复创建。
    """
    print("=" * 60)
    print("日本陆上养殖数据处理系统 - 数据库初始化")
    print("=" * 60)
    print()
    print("正在创建应用上下文...")
    
    app = create_app()
    
    with app.app_context():
        print("正在创建数据库表...")
        db.create_all()
        print()
        print("✓ 数据库表已成功创建或更新！")
        print()
        
        # 验证表是否创建成功
        print("正在验证数据库结构...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"✓ 数据库验证成功！共创建 {len(tables)} 个表")
            print()
            print("数据库表列表：")
            for table in sorted(tables):
                print(f"  - {table}")
        else:
            print("⚠ 警告：未检测到表，请检查配置")
        
        print()
        print("=" * 60)
        print("初始化完成！")
        print("=" * 60)


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

