#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 sensor_readings 模型以匹配实际数据库表结构

根据实际数据库表结构，调整模型定义
"""
from database import get_db
from sqlalchemy import text, inspect

def check_table_structure():
    """检查实际表结构"""
    with get_db() as db:
        # 获取表结构
        result = db.execute(text('DESCRIBE sensor_readings'))
        columns = {}
        for row in result:
            columns[row[0]] = {
                'type': row[1],
                'null': row[2],
                'key': row[3],
                'default': row[4],
            }
        
        return columns

def main():
    """主函数"""
    print("检查 sensor_readings 表结构...")
    columns = check_table_structure()
    
    print("\n实际表字段:")
    for col_name in sorted(columns.keys()):
        col_info = columns[col_name]
        print(f"  - {col_name}: {col_info['type']}")
    
    # 检查关键字段
    has_device_id = 'device_id' in columns
    has_sensor_id = 'sensor_id' in columns
    has_ts_utc = 'ts_utc' in columns
    has_recorded_at = 'recorded_at' in columns
    
    print("\n字段检查:")
    print(f"  device_id: {'✓' if has_device_id else '✗'}")
    print(f"  sensor_id: {'✓' if has_sensor_id else '✗'}")
    print(f"  ts_utc: {'✓' if has_ts_utc else '✗'}")
    print(f"  recorded_at: {'✓' if has_recorded_at else '✗'}")
    
    if has_sensor_id and not has_device_id:
        print("\n⚠️  检测到表使用 sensor_id 而不是 device_id")
        print("   需要修改模型定义以匹配实际表结构")
        return "sensor_id"
    elif has_device_id:
        print("\n✓ 表结构使用 device_id，与模型定义匹配")
        return "device_id"
    else:
        print("\n⚠️  未找到 device_id 或 sensor_id 字段")
        return None

if __name__ == "__main__":
    result = main()
    if result == "sensor_id":
        print("\n建议:")
        print("1. 执行数据库迁移脚本添加 device_id 字段")
        print("2. 或修改模型使用 sensor_id（临时方案）")

