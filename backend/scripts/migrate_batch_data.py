#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次数据迁移脚本
将旧的batches.csv数据迁移到新的数据库表设计中
"""

import sys
import os
from datetime import datetime
from decimal import Decimal

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
# 导入所有模型以确保 SQLAlchemy 能够正确解析关系
import db_models  # 这会触发 __init__.py 中的所有导入
from db_models.batch import Batch
from db_models.pond import Pond
from sqlalchemy import text


def migrate_batch_data():
    """
    迁移批次数据
    
    旧数据:
    - batch_id: 2
    - species: Litopenaeus vannamei
    - pool_id: 4 (字符串类型)
    - location: つくば
    - seed_origin: (空)
    - stocking_density: 500.00
    - start_date: 2025-10-16
    - end_date: 2026-01-16
    - notes: (空)
    - created_at: 2025-12-04 18:39:16
    - updated_at: 2025-12-15 13:59:04
    
    新表结构:
    - pond_id: INTEGER 外键引用 ponds.id
    """
    
    try:
        with db_session_factory() as session:
            # 1. 查找对应的pond记录
            # 旧数据中pool_id=4，location=つくば
            # 现有ponds表中只有一条记录: id=1, name="四号", location="つくば"
            # 推测pool_id=4指的是"四号养殖池"，映射到pond_id=1
            
            pond = session.query(Pond).filter(Pond.id == 1).first()
            
            if not pond:
                print("❌ 未找到id=1的养殖池，无法迁移数据")
                print("提示：请先确保ponds表中存在对应的养殖池记录")
                return False
            
            print(f"✓ 找到养殖池: {pond.name} (id={pond.id}, location={pond.location})")
            
            # 2. 检查batch_id=2是否已存在
            existing_batch = session.query(Batch).filter(Batch.batch_id == 2).first()
            
            if existing_batch:
                print(f"⚠️  batch_id=2 已存在，是否需要更新？")
                print(f"   现有数据: pond_id={existing_batch.pond_id}, start_date={existing_batch.start_date}")
                
                # 更新现有记录
                existing_batch.pond_id = 1
                existing_batch.species = "Litopenaeus vannamei"
                existing_batch.location = "つくば"
                existing_batch.seed_origin = None
                existing_batch.stocking_density = Decimal("500.00")
                existing_batch.start_date = datetime.strptime("2025-10-16", "%Y-%m-%d").date()
                existing_batch.end_date = datetime.strptime("2026-01-16", "%Y-%m-%d").date()
                existing_batch.notes = None
                
                session.commit()
                print("✓ 批次数据已更新")
                
            else:
                # 3. 创建新的batch记录
                new_batch = Batch(
                    pond_id=1,  # 映射到ponds.id=1
                    start_date=datetime.strptime("2025-10-16", "%Y-%m-%d").date()
                )
                
                # 设置可选字段
                new_batch.species = "Litopenaeus vannamei"
                new_batch.location = "つくば"
                new_batch.seed_origin = None  # 原数据为空
                new_batch.stocking_density = Decimal("500.00")
                new_batch.end_date = datetime.strptime("2026-01-16", "%Y-%m-%d").date()
                new_batch.notes = None  # 原数据为空
                
                session.add(new_batch)
                session.commit()
                
                print(f"✓ 批次数据迁移成功！")
                print(f"  - batch_id: {new_batch.batch_id}")
                print(f"  - pond_id: {new_batch.pond_id}")
                print(f"  - species: {new_batch.species}")
                print(f"  - location: {new_batch.location}")
                print(f"  - stocking_density: {new_batch.stocking_density}")
                print(f"  - start_date: {new_batch.start_date}")
                print(f"  - end_date: {new_batch.end_date}")
                print(f"  - created_at: {new_batch.created_at}")
            
            # 4. 验证数据
            print("\n验证迁移结果:")
            batch_count = session.query(Batch).count()
            print(f"  - batches表总记录数: {batch_count}")
            
            # 查询刚插入或更新的记录
            batch = session.query(Batch).filter(Batch.pond_id == 1).first()
            if batch:
                print(f"  - 找到批次记录: batch_id={batch.batch_id}, pond={batch.pond.name}")
            
            return True
            
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("批次数据迁移脚本")
    print("=" * 60)
    print()
    
    success = migrate_batch_data()
    
    print()
    print("=" * 60)
    if success:
        print("✓ 迁移完成")
    else:
        print("❌ 迁移失败，请检查错误信息")
    print("=" * 60)

