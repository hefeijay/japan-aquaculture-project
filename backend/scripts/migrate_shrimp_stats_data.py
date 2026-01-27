#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虾统计数据迁移脚本
迁移 shrimp_stats.csv 到新的表结构
"""

import sys
import os
import csv
from datetime import datetime
from decimal import Decimal

# 添加 backend 目录到路径
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db_models.db_session import db_session_factory
import db_models  # 导入所有模型
from db_models.shrimp_stats import ShrimpStats
from db_models.batch import Batch
from sqlalchemy import text


def parse_datetime(date_str):
    """解析多种格式的时间字符串"""
    if not date_str:
        return None
    
    # 尝试多种格式
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None


def migrate_shrimp_stats(session):
    """迁移 shrimp_stats.csv 数据"""
    print("=" * 60)
    print("步骤 1: 迁移虾统计数据 (shrimp_stats.csv)")
    print("=" * 60)
    
    csv_path = os.path.join(backend_dir, 'db_models/db_datas/shrimp_stats.csv')
    
    if not os.path.exists(csv_path):
        print(f"  ⚠️  文件不存在: {csv_path}")
        return 0
    
    # 检查 batch_id=1 是否存在
    batch_exists = session.query(Batch).filter(Batch.batch_id == 1).first() is not None
    if not batch_exists:
        print(f"  ⚠️  警告: batches 表中不存在 batch_id=1，将跳过 batch_id 字段")
    else:
        print(f"  ✓ 批次数据已就绪: batch_id=1")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # 检查是否已存在（根据 id）
                if row.get('id'):
                    stat_id = int(row['id'])
                    existing = session.query(ShrimpStats).filter(ShrimpStats.id == stat_id).first()
                    if existing:
                        skip_count += 1
                        continue
                
                # 解析时间
                ts_utc = None
                if row.get('ts_utc'):
                    ts_utc = parse_datetime(row['ts_utc'])
                elif row.get('created_at_source_iso'):
                    ts_utc = parse_datetime(row['created_at_source_iso'])
                elif row.get('created_at_source'):
                    ts_utc = parse_datetime(row['created_at_source'])
                
                if not ts_utc:
                    # 如果没有时间，使用当前时间
                    ts_utc = datetime.utcnow()
                
                # CSV 中的 pond_id 是字符串类型（如 "camera_0_1765775944"），需要映射到实际的 pond_id=1
                # 所有数据都属于同一个池子
                pond_id = 1
                
                # 创建 ShrimpStats 记录（只传必需参数）
                shrimp_stat = ShrimpStats(
                    ts_utc=ts_utc,
                    pond_id=pond_id
                )
                
                # 设置可选字段（标记了 init=False）
                if row.get('frame_id'):
                    try:
                        shrimp_stat.frame_id = int(row['frame_id'])
                    except:
                        pass
                
                # 映射 batch_id
                if batch_exists:
                    # 所有数据都属于 batch_id=1
                    shrimp_stat.batch_id = 1
                
                if row.get('uuid'):
                    shrimp_stat.uuid = row['uuid']
                if row.get('input_subdir'):
                    shrimp_stat.input_subdir = row['input_subdir']
                if row.get('output_dir'):
                    shrimp_stat.output_dir = row['output_dir']
                if row.get('created_at_source_iso'):
                    shrimp_stat.created_at_source_iso = row['created_at_source_iso']
                if row.get('created_at_source'):
                    parsed = parse_datetime(row['created_at_source'])
                    if parsed:
                        shrimp_stat.created_at_source = parsed
                
                # 数值字段
                if row.get('conf'):
                    try:
                        shrimp_stat.conf = float(row['conf'])
                    except:
                        pass
                if row.get('confidence_avg'):
                    try:
                        shrimp_stat.confidence_avg = Decimal(str(row['confidence_avg']))
                    except:
                        pass
                if row.get('iou'):
                    try:
                        shrimp_stat.iou = float(row['iou'])
                    except:
                        pass
                if row.get('total_live'):
                    try:
                        shrimp_stat.total_live = int(row['total_live'])
                    except:
                        pass
                if row.get('count'):
                    try:
                        shrimp_stat.count = int(row['count'])
                    except:
                        pass
                if row.get('total_dead'):
                    try:
                        shrimp_stat.total_dead = int(row['total_dead'])
                    except:
                        pass
                
                # 尺寸字段
                if row.get('size_min_cm'):
                    try:
                        shrimp_stat.size_min_cm = float(row['size_min_cm'])
                    except:
                        pass
                if row.get('size_max_cm'):
                    try:
                        shrimp_stat.size_max_cm = float(row['size_max_cm'])
                    except:
                        pass
                if row.get('size_mean_cm'):
                    try:
                        shrimp_stat.size_mean_cm = float(row['size_mean_cm'])
                    except:
                        pass
                if row.get('size_median_cm'):
                    try:
                        shrimp_stat.size_median_cm = float(row['size_median_cm'])
                    except:
                        pass
                if row.get('avg_length_mm'):
                    try:
                        shrimp_stat.avg_length_mm = Decimal(str(row['avg_length_mm']))
                    except:
                        pass
                if row.get('avg_height_mm'):
                    try:
                        shrimp_stat.avg_height_mm = Decimal(str(row['avg_height_mm']))
                    except:
                        pass
                
                # 体重字段
                if row.get('weight_min_g'):
                    try:
                        shrimp_stat.weight_min_g = float(row['weight_min_g'])
                    except:
                        pass
                if row.get('weight_max_g'):
                    try:
                        shrimp_stat.weight_max_g = float(row['weight_max_g'])
                    except:
                        pass
                if row.get('weight_mean_g'):
                    try:
                        shrimp_stat.weight_mean_g = float(row['weight_mean_g'])
                    except:
                        pass
                if row.get('weight_median_g'):
                    try:
                        shrimp_stat.weight_median_g = float(row['weight_median_g'])
                    except:
                        pass
                if row.get('est_weight_g_avg'):
                    try:
                        shrimp_stat.est_weight_g_avg = Decimal(str(row['est_weight_g_avg']))
                    except:
                        pass
                
                # 布尔字段
                if row.get('feed_present'):
                    shrimp_stat.feed_present = row['feed_present'].lower() == 'true'
                if row.get('shrimp_shell_present'):
                    shrimp_stat.shrimp_shell_present = row['shrimp_shell_present'].lower() == 'true'
                
                # 模型信息
                if row.get('model_name'):
                    shrimp_stat.model_name = row['model_name']
                if row.get('model_version'):
                    shrimp_stat.model_version = row['model_version']
                
                # 其他字段
                if row.get('notes'):
                    shrimp_stat.notes = row['notes']
                if row.get('source_file'):
                    shrimp_stat.source_file = row['source_file']
                
                session.add(shrimp_stat)
                success_count += 1
                
                if success_count % 50 == 0:
                    session.flush()
                    print(f"  进度: 已处理 {success_count} 条记录...")
                    
            except Exception as e:
                error_count += 1
                session.rollback()
                if error_count <= 10:  # 只显示前10个错误
                    print(f"  ❌ 处理记录失败 (id={row.get('id', '?')}): {e}")
                continue
    
    session.commit()
    
    print(f"\n  ✓ shrimp_stats.csv 迁移完成:")
    print(f"    - 成功: {success_count} 条")
    print(f"    - 跳过: {skip_count} 条")
    print(f"    - 失败: {error_count} 条")
    
    return success_count


def verify_migration(session):
    """步骤2: 验证迁移结果"""
    print("\n" + "=" * 60)
    print("步骤 2: 验证迁移结果")
    print("=" * 60)
    
    # 统计数据
    total_count = session.query(ShrimpStats).count()
    with_count = session.query(ShrimpStats).filter(ShrimpStats.count.isnot(None), ShrimpStats.count > 0).count()
    
    print(f"  ✓ 数据统计:")
    print(f"    - 总记录数: {total_count} 条")
    print(f"    - 有检测数量的记录: {with_count} 条")
    
    # 时间范围
    result = session.query(ShrimpStats).order_by(ShrimpStats.ts_utc.asc()).first()
    if result:
        min_date = result.ts_utc
        result = session.query(ShrimpStats).order_by(ShrimpStats.ts_utc.desc()).first()
        max_date = result.ts_utc
        print(f"\n  ✓ 数据时间范围:")
        print(f"    - {min_date} ~ {max_date}")
    
    # 统计信息
    result = session.execute(text("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN count > 0 THEN count ELSE 0 END) as total_shrimp_detected,
            AVG(CASE WHEN size_mean_cm > 0 THEN size_mean_cm ELSE NULL END) as avg_size,
            AVG(CASE WHEN weight_mean_g > 0 THEN weight_mean_g ELSE NULL END) as avg_weight
        FROM shrimp_stats
    """)).first()
    
    if result:
        print(f"\n  ✓ 检测统计:")
        print(f"    - 总记录数: {result[0]} 条")
        print(f"    - 检测到虾总数: {int(result[1]) if result[1] else 0} 只")
        if result[2]:
            print(f"    - 平均尺寸: {float(result[2]):.2f} cm")
        if result[3]:
            print(f"    - 平均体重: {float(result[3]):.2f} g")
    
    print()


def main():
    """主函数"""
    print("=" * 60)
    print("虾统计数据迁移脚本")
    print("=" * 60)
    print()
    
    try:
        with db_session_factory() as session:
            # 步骤1: 迁移虾统计数据
            stats_count = migrate_shrimp_stats(session)
            
            if stats_count == 0:
                print("\n⚠️  没有虾统计数据需要迁移")
                return False
            
            # 步骤2: 验证迁移结果
            verify_migration(session)
            
            print("=" * 60)
            print("✅ 虾统计数据迁移成功完成！")
            print("=" * 60)
            return True
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

