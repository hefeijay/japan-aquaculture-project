#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 sensor_types 表：
1. 查看 sensor_types 表
2. 删除 id=6 的记录
3. 补全 id=1 的 unit
4. 补全 id=3 (PH) 的 unit
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
from japan_server.db_models.sensor_type import SensorType

def view_sensor_types():
    """查看所有 sensor_types 记录"""
    with db_session_factory() as session:
        types = session.query(SensorType).order_by(SensorType.id).all()
        print(f"\n{'='*80}")
        print(f"sensor_types 表所有记录 ({len(types)} 条):")
        print(f"{'='*80}\n")
        
        for st in types:
            print(f"ID: {st.id}")
            print(f"  type_name: {st.type_name}")
            print(f"  unit: {st.unit}")
            print(f"  description: {st.description}")
            print()

def delete_sensor_type(id_to_delete):
    """删除指定 ID 的 sensor_type（需要先处理引用的 sensors）"""
    from japan_server.db_models.sensor import Sensor
    from sqlalchemy import text
    
    with db_session_factory() as session:
        st = session.query(SensorType).filter(SensorType.id == id_to_delete).first()
        if not st:
            print(f"未找到 ID={id_to_delete} 的记录")
            return False
        
        # 检查是否有 sensors 引用这个 sensor_type
        sensors = session.query(Sensor).filter(Sensor.sensor_type_id == id_to_delete).all()
        if sensors:
            print(f"警告: 有 {len(sensors)} 个 sensors 记录引用了 sensor_type_id={id_to_delete}")
            print("需要先删除或更新这些 sensors 记录")
            for s in sensors:
                print(f"  sensor_id={s.id}, name={s.name}")
            
            # 先删除引用的 sensors 记录
            print(f"\n删除引用的 sensors 记录...")
            for s in sensors:
                session.delete(s)
            session.commit()
            print(f"✓ 已删除 {len(sensors)} 个引用的 sensors 记录")
        
        print(f"\n准备删除 ID={id_to_delete} 的记录:")
        print(f"  type_name: {st.type_name}")
        print(f"  unit: {st.unit}")
        print(f"  description: {st.description}")
        
        session.delete(st)
        session.commit()
        print(f"✓ 已删除 ID={id_to_delete} 的记录")
        return True

def update_sensor_type_unit(id_to_update, unit):
    """更新指定 ID 的 sensor_type 的 unit"""
    with db_session_factory() as session:
        st = session.query(SensorType).filter(SensorType.id == id_to_update).first()
        if not st:
            print(f"未找到 ID={id_to_update} 的记录")
            return False
        
        old_unit = st.unit
        print(f"更新 ID={id_to_update} 的记录:")
        print(f"  type_name: {st.type_name}")
        print(f"  unit: {old_unit} -> {unit}")
        
        st.unit = unit
        session.add(st)
        session.commit()
        print(f"✓ 已更新 ID={id_to_update} 的 unit")
        return True

def update_sensor_type_name(id_to_update, type_name):
    """更新指定 ID 的 sensor_type 的 type_name"""
    with db_session_factory() as session:
        st = session.query(SensorType).filter(SensorType.id == id_to_update).first()
        if not st:
            print(f"未找到 ID={id_to_update} 的记录")
            return False
        
        old_type_name = st.type_name
        print(f"更新 ID={id_to_update} 的记录:")
        print(f"  type_name: {old_type_name} -> {type_name}")
        print(f"  unit: {st.unit}")
        
        st.type_name = type_name
        session.add(st)
        session.commit()
        print(f"✓ 已更新 ID={id_to_update} 的 type_name")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='修复 sensor_types 表')
    parser.add_argument('--view', action='store_true', help='查看所有记录')
    parser.add_argument('--delete', type=int, help='删除指定 ID 的记录')
    parser.add_argument('--update-unit', nargs=2, metavar=('ID', 'UNIT'), help='更新指定 ID 的 unit')
    parser.add_argument('--update-name', nargs=2, metavar=('ID', 'NAME'), help='更新指定 ID 的 type_name')
    parser.add_argument('--execute', action='store_true', help='执行所有修复操作')
    
    args = parser.parse_args()
    
    if args.view:
        view_sensor_types()
    
    if args.delete:
        if not args.execute:
            print("请使用 --execute 参数确认删除操作")
            return
        delete_sensor_type(args.delete)
    
    if args.update_unit:
        if not args.execute:
            print("请使用 --execute 参数确认更新操作")
            return
        id_to_update, unit = args.update_unit
        update_sensor_type_unit(int(id_to_update), unit)
    
    if args.update_name:
        if not args.execute:
            print("请使用 --execute 参数确认更新操作")
            return
        id_to_update, type_name = args.update_name
        update_sensor_type_name(int(id_to_update), type_name)
    
    # 执行所有修复操作
    if args.execute and not args.delete and not args.update_unit:
        print("\n执行所有修复操作:")
        print("1. 查看当前记录")
        view_sensor_types()
        
        print("\n2. 删除 ID=6 的记录")
        delete_sensor_type(6)
        
        print("\n3. 更新 ID=1 的 unit 为 'mg/L'")
        update_sensor_type_unit(1, 'mg/L')
        
        print("\n4. 更新 ID=3 的 unit 为 'pH'")
        update_sensor_type_unit(3, 'pH')
        
        print("\n5. 查看修复后的记录")
        view_sensor_types()

if __name__ == '__main__':
    main()

