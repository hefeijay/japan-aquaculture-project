#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 ponds 表添加 area 和 count 字段的迁移脚本
执行方式: python3 add_pond_fields.py
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from sqlalchemy import text

def add_pond_fields():
    """为 ponds 表添加 area 和 count 字段"""
    try:
        with db_session_factory() as session:
            # 检查字段是否已存在
            result = session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'ponds' 
                AND COLUMN_NAME IN ('area', 'count')
            """))
            existing_columns = [row[0] for row in result]
            
            # 添加 area 字段（如果不存在）
            if 'area' not in existing_columns:
                print("正在添加 area 字段...")
                session.execute(text("""
                    ALTER TABLE ponds 
                    ADD COLUMN area FLOAT NULL COMMENT '养殖池实际面积（平方米）' 
                    AFTER location
                """))
                print("✓ area 字段添加成功")
            else:
                print("✓ area 字段已存在，跳过")
            
            # 添加 count 字段（如果不存在）
            if 'count' not in existing_columns:
                print("正在添加 count 字段...")
                session.execute(text("""
                    ALTER TABLE ponds 
                    ADD COLUMN count INT NULL COMMENT '养殖池实际统计的数量（尾数）' 
                    AFTER area
                """))
                print("✓ count 字段添加成功")
            else:
                print("✓ count 字段已存在，跳过")
            
            session.commit()
            print("\n✓ 数据库迁移完成！")
            
            # 显示表结构
            print("\n当前 ponds 表结构:")
            result = session.execute(text("DESCRIBE ponds"))
            for row in result:
                print(f"  {row[0]:<20} {row[1]:<20} {row[2]:<10} {row[3]:<10} {row[4] or ''}")
            
    except Exception as e:
        print(f"✗ 数据库迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("ponds 表字段迁移脚本")
    print("=" * 60)
    print()
    
    success = add_pond_fields()
    
    if success:
        print("\n" + "=" * 60)
        print("迁移成功！现在可以使用新的 area 和 count 字段了。")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("迁移失败！请检查错误信息。")
        print("=" * 60)
        sys.exit(1)

