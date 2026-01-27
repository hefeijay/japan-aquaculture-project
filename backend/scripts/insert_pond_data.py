#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入养殖池数据
根据 ponds.csv 文件插入基础数据
"""

import sys
import os

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
import db_models  # 导入所有模型
from db_models.pond import Pond
from sqlalchemy import text


def insert_pond_data():
    """
    插入养殖池数据
    
    根据 ponds.csv:
    id=1, name="四号", location="つくば", area=7, count=3576
    """
    
    try:
        with db_session_factory() as session:
            # 检查是否已存在
            existing_pond = session.query(Pond).filter(Pond.id == 1).first()
            
            if existing_pond:
                print(f"✓ 养殖池已存在: {existing_pond.name} (id={existing_pond.id})")
                print(f"  - location: {existing_pond.location}")
                print(f"  - area: {existing_pond.area}")
                print(f"  - count: {existing_pond.count}")
                return True
            
            # 创建新的养殖池记录
            print("正在插入养殖池数据...")
            new_pond = Pond(
                name="四号",
                location="つくば",
                area=7.0,
                count=3576,
                description="四号养殖池"
            )
            
            session.add(new_pond)
            session.commit()
            
            print(f"✓ 养殖池数据插入成功！")
            print(f"  - id: {new_pond.id}")
            print(f"  - name: {new_pond.name}")
            print(f"  - location: {new_pond.location}")
            print(f"  - area: {new_pond.area}")
            print(f"  - count: {new_pond.count}")
            print(f"  - created_at: {new_pond.created_at}")
            
            return True
            
    except Exception as e:
        print(f"❌ 插入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("养殖池数据插入脚本")
    print("=" * 60)
    print()
    
    success = insert_pond_data()
    
    print()
    print("=" * 60)
    if success:
        print("✓ 操作完成")
    else:
        print("❌ 操作失败")
    print("=" * 60)

