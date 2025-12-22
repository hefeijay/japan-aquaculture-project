#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 sensor_types 表的 metric 映射数据
执行方式: python3 init_sensor_type_metrics.py
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from sqlalchemy import text

# metric 到 type_name 的映射关系
METRIC_MAPPINGS = [
    {"metric": "temperature", "type_name": "temperature", "unit": "°C", "description": "水温传感器"},
    {"metric": "turbidity", "type_name": "turbidity", "unit": "NTU", "description": "浊度传感器"},
    {"metric": "do", "type_name": "dissolved_oxygen_aturation", "unit": "%", "description": "溶解氧传感器"},
    {"metric": "water_level", "type_name": "liquid_level", "unit": "mm", "description": "液位传感器"},
    {"metric": "ph", "type_name": "ph", "unit": "pH", "description": "pH值传感器"},
    # 支持大小写变体
    {"metric": "pH", "type_name": "ph", "unit": "pH", "description": "pH值传感器"},
    {"metric": "PH", "type_name": "ph", "unit": "pH", "description": "pH值传感器"},
]

def init_sensor_type_metrics():
    """初始化 sensor_types 表的 metric 映射数据"""
    try:
        with db_session_factory() as session:
            print("开始初始化 sensor_types 表的 metric 映射数据...")
            print()
            
            updated_count = 0
            created_count = 0
            
            for mapping in METRIC_MAPPINGS:
                metric = mapping["metric"]
                type_name = mapping["type_name"]
                unit = mapping.get("unit", "")
                description = mapping.get("description", "")
                
                # 检查是否已存在该 type_name 的记录
                result = session.execute(
                    text("SELECT id, metric FROM sensor_types WHERE type_name = :type_name"),
                    {"type_name": type_name}
                ).first()
                
                if result:
                    sensor_type_id, existing_metric = result
                    # 如果 metric 字段为空或不同，则更新
                    if existing_metric != metric:
                        session.execute(
                            text("UPDATE sensor_types SET metric = :metric WHERE id = :id"),
                            {"metric": metric, "id": sensor_type_id}
                        )
                        print(f"✓ 更新: type_name='{type_name}' -> metric='{metric}'")
                        updated_count += 1
                    else:
                        print(f"  - 跳过: type_name='{type_name}' 已有 metric='{metric}'")
                else:
                    # 如果不存在，创建新记录
                    session.execute(
                        text("""
                            INSERT INTO sensor_types (type_name, metric, unit, description)
                            VALUES (:type_name, :metric, :unit, :description)
                        """),
                        {
                            "type_name": type_name,
                            "metric": metric,
                            "unit": unit,
                            "description": description
                        }
                    )
                    print(f"✓ 创建: type_name='{type_name}', metric='{metric}'")
                    created_count += 1
            
            session.commit()
            print()
            print(f"✓ 初始化完成！创建 {created_count} 条记录，更新 {updated_count} 条记录")
            
            # 显示当前所有映射关系
            print("\n当前 sensor_types 表的 metric 映射:")
            result = session.execute(text("""
                SELECT id, type_name, metric, unit, description 
                FROM sensor_types 
                WHERE metric IS NOT NULL 
                ORDER BY type_name
            """))
            print(f"{'ID':<5} {'type_name':<30} {'metric':<20} {'unit':<10} {'description':<30}")
            print("-" * 100)
            for row in result:
                print(f"{row[0]:<5} {row[1]:<30} {row[2] or 'NULL':<20} {row[3] or 'NULL':<10} {row[4] or 'NULL':<30}")
            
    except Exception as e:
        print(f"✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("sensor_types 表 metric 映射数据初始化脚本")
    print("=" * 60)
    print()
    
    success = init_sensor_type_metrics()
    
    if success:
        print("\n" + "=" * 60)
        print("初始化成功！现在可以使用数据库中的 metric 映射了。")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("初始化失败！请检查错误信息。")
        print("=" * 60)
        sys.exit(1)

