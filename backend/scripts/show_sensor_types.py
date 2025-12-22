#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示sensor_types表的所有内容
"""

import sys
import os

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
parent_root = os.path.dirname(project_root)
if parent_root not in sys.path:
    sys.path.insert(0, parent_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_type import SensorType
from sqlalchemy import text

def show_sensor_types():
    """显示sensor_types表的所有内容"""
    print("=" * 100)
    print("sensor_types 表的所有记录")
    print("=" * 100)
    
    try:
        with db_session_factory() as session:
            # 查询所有记录
            types = session.query(SensorType).order_by(SensorType.id).all()
            
            if not types:
                print("⚠ 警告: sensor_types 表为空")
                return
            
            print(f"\n共找到 {len(types)} 条记录:\n")
            print(f"{'ID':<5} {'类型名称':<40} {'Metric':<25} {'单位':<15} {'描述':<50}")
            print("-" * 140)
            
            for st in types:
                type_name = st.type_name or ""
                metric = st.metric or ""
                unit = st.unit or ""
                description = st.description or ""
                # 如果描述太长，截断
                if len(description) > 48:
                    description = description[:48] + ".."
                
                print(f"{st.id:<5} {type_name:<40} {metric:<25} {unit:<15} {description:<50}")
            
            print("\n" + "=" * 100)
            print("详细信息（JSON格式）:")
            print("=" * 100)
            for st in types:
                print(f"\nID: {st.id}")
                print(f"  类型名称: {st.type_name}")
                print(f"  Metric: {st.metric}")
                print(f"  单位: {st.unit}")
                print(f"  描述: {st.description}")
                
    except Exception as e:
        print(f"✗ 查询失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    show_sensor_types()










