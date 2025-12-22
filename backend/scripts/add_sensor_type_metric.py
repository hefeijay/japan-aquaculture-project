#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 sensor_types 表添加 metric 字段的迁移脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from japan_server.db_models.db_session import db_session_factory

def add_metric_column():
    """为 sensor_types 表添加 metric 字段"""
    try:
        with db_session_factory() as session:
            # 检查字段是否已存在
            result = session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'sensor_types' 
                AND COLUMN_NAME = 'metric'
            """))
            
            if result.first():
                print("✓ metric 字段已存在，跳过添加")
                return True
            
            # 添加 metric 字段
            session.execute(text("""
                ALTER TABLE sensor_types 
                ADD COLUMN metric VARCHAR(64) NULL UNIQUE COMMENT 'metric 标识符，用于数据接收时的映射' 
                AFTER type_name
            """))
            session.commit()
            print("✓ 成功添加 metric 字段到 sensor_types 表")
            return True
            
    except Exception as e:
        print(f"✗ 添加 metric 字段失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("为 sensor_types 表添加 metric 字段")
    print("=" * 60)
    add_metric_column()

