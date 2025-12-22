#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查 sensor_readings 表的最新记录
"""

import sys
import os

# 添加项目根目录的父目录到路径，使 japan_server 可以作为包导入
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
parent_dir = os.path.dirname(project_root)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_reading import SensorReading

def check_latest_records(limit=5):
    """查看最新的记录"""
    with db_session_factory() as session:
        # 查询最新的记录
        latest = session.query(SensorReading).order_by(
            SensorReading.id.desc()
        ).limit(limit).all()
        
        print(f"\n{'='*80}")
        print(f"sensor_readings 表最新 {len(latest)} 条记录:")
        print(f"{'='*80}\n")
        
        for i, record in enumerate(latest, 1):
            print(f"记录 #{i} (ID: {record.id})")
            print(f"  sensor_id: {record.sensor_id}")
            print(f"  metric: {record.metric}")
            print(f"  value: {record.value}")
            print(f"  type_name: {record.type_name}")
            print(f"  unit: {record.unit}")
            print(f"  description: {record.description}")
            print(f"  pool_id: {record.pool_id}")
            print(f"  batch_id: {record.batch_id}")
            print(f"  recorded_at: {record.recorded_at}")
            print()
            
            # 检查是否有问题
            issues = []
            if record.metric == 'temperature' and record.type_name and '温度' not in record.type_name and 'pH' not in record.type_name and '浊度' not in record.type_name:
                issues.append(f"⚠️  metric='temperature' 但 type_name='{record.type_name}' 可能不正确")
            if record.metric == 'turbidity' and record.type_name and '浊度' not in record.type_name:
                issues.append(f"⚠️  metric='turbidity' 但 type_name='{record.type_name}' 可能不正确")
            if record.metric == 'ph' and record.type_name and 'pH' not in record.type_name and 'ph' not in record.type_name.lower():
                issues.append(f"⚠️  metric='ph' 但 type_name='{record.type_name}' 可能不正确")
            if record.unit is None:
                issues.append("⚠️  unit 字段为 None")
            if record.description and ('温度' in record.description and record.metric != 'temperature'):
                issues.append(f"⚠️  description 可能不正确: {record.description}")
            
            if issues:
                print("  问题:")
                for issue in issues:
                    print(f"    {issue}")
                print()
            else:
                print("  ✓ 未发现问题\n")
        
        print(f"{'='*80}\n")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='检查 sensor_readings 表的最新记录')
    parser.add_argument('--limit', type=int, default=5, help='查看的记录数（默认5条）')
    args = parser.parse_args()
    
    check_latest_records(args.limit)






















