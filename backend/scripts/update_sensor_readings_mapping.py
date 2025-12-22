#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 sensor_readings 表中已有数据的 metric 和 type_name 映射关系
根据 sensor_types 表中的映射关系，修正 sensor_readings 表中的数据

执行方式: python3 update_sensor_readings_mapping.py [--dry-run] [--limit N]
"""

import sys
import os
import argparse

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from sqlalchemy import text

def update_sensor_readings_mapping(dry_run=False, limit=None):
    """
    更新 sensor_readings 表中已有数据的 metric 和 type_name 映射关系
    
    Args:
        dry_run: 如果为 True，只显示将要更新的数据，不实际更新
        limit: 限制更新的记录数量（用于测试）
    """
    try:
        with db_session_factory() as session:
            print("=" * 60)
            print("更新 sensor_readings 表的 metric 和 type_name 映射")
            print("=" * 60)
            print()
            
            if dry_run:
                print("⚠  DRY RUN 模式：只显示将要更新的数据，不会实际修改数据库")
                print()
            
            # 1. 首先获取所有需要更新的记录（metric 或 type_name 不为空，但可能映射不正确）
            print("1. 查询需要更新的记录...")
            
            # 查询所有有 metric 或 type_name 的记录
            query = """
                SELECT 
                    sr.id,
                    sr.metric,
                    sr.type_name,
                    sr.sensor_id,
                    s.sensor_type_id,
                    st.type_name as sensor_type_name,
                    st.metric as sensor_type_metric
                FROM sensor_readings sr
                LEFT JOIN sensors s ON sr.sensor_id = s.id
                LEFT JOIN sensor_types st ON s.sensor_type_id = st.id
                WHERE (sr.metric IS NOT NULL OR sr.type_name IS NOT NULL)
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = session.execute(text(query))
            records = result.fetchall()
            
            print(f"   找到 {len(records)} 条记录需要检查")
            print()
            
            # 2. 获取 sensor_types 表中的所有映射关系
            print("2. 加载 sensor_types 映射关系...")
            mapping_result = session.execute(text("""
                SELECT type_name, metric 
                FROM sensor_types 
                WHERE metric IS NOT NULL
            """))
            
            # 创建双向映射字典
            metric_to_type_name = {}
            type_name_to_metric = {}
            
            for row in mapping_result:
                type_name, metric = row
                if metric:
                    metric_to_type_name[metric.lower()] = type_name
                    type_name_to_metric[type_name.lower()] = metric
            
            print(f"   加载了 {len(metric_to_type_name)} 个映射关系")
            print()
            
            # 3. 分析每条记录，确定需要更新的字段
            print("3. 分析记录并准备更新...")
            print()
            
            updates_needed = []
            stats = {
                "total": len(records),
                "no_update_needed": 0,
                "update_metric": 0,
                "update_type_name": 0,
                "update_both": 0,
                "use_sensor_type": 0,
                "no_mapping_found": 0,
            }
            
            for record in records:
                record_id, current_metric, current_type_name, sensor_id, sensor_type_id, sensor_type_name, sensor_type_metric = record
                
                # 确定应该使用的 metric 和 type_name
                target_metric = None
                target_type_name = None
                update_reason = []
                
                # 策略1: 如果 sensor_type 存在，优先使用 sensor_type 的映射
                if sensor_type_name:
                    # 从 sensor_types 表获取对应的 metric
                    if sensor_type_metric:
                        target_metric = sensor_type_metric
                        target_type_name = sensor_type_name
                        update_reason.append("使用 sensor_type 映射")
                        stats["use_sensor_type"] += 1
                    else:
                        # 如果 sensor_type 没有 metric，尝试从 type_name 查询
                        mapped_metric = type_name_to_metric.get(sensor_type_name.lower())
                        if mapped_metric:
                            target_metric = mapped_metric
                            target_type_name = sensor_type_name
                            update_reason.append("从 type_name 查询 metric")
                        else:
                            target_type_name = sensor_type_name
                            update_reason.append("使用 sensor_type.type_name")
                
                # 策略2: 如果当前有 metric，尝试从 metric 查询 type_name
                if current_metric and not target_type_name:
                    mapped_type_name = metric_to_type_name.get(current_metric.lower())
                    if mapped_type_name:
                        target_type_name = mapped_type_name
                        target_metric = current_metric
                        update_reason.append("从 metric 查询 type_name")
                
                # 策略3: 如果当前有 type_name，尝试从 type_name 查询 metric
                if current_type_name and not target_metric:
                    mapped_metric = type_name_to_metric.get(current_type_name.lower())
                    if mapped_metric:
                        target_metric = mapped_metric
                        target_type_name = current_type_name
                        update_reason.append("从 type_name 查询 metric")
                
                # 检查是否需要更新
                needs_update = False
                update_fields = []
                
                if target_metric and target_metric != current_metric:
                    needs_update = True
                    update_fields.append("metric")
                    stats["update_metric"] += 1
                
                if target_type_name and target_type_name != current_type_name:
                    needs_update = True
                    update_fields.append("type_name")
                    stats["update_type_name"] += 1
                
                if needs_update:
                    updates_needed.append({
                        "id": record_id,
                        "current_metric": current_metric,
                        "current_type_name": current_type_name,
                        "target_metric": target_metric,
                        "target_type_name": target_type_name,
                        "update_fields": update_fields,
                        "reason": ", ".join(update_reason) if update_reason else "未知",
                        "sensor_id": sensor_id,
                        "sensor_type_name": sensor_type_name,
                    })
                    if len(update_fields) == 2:
                        stats["update_both"] += 1
                else:
                    stats["no_update_needed"] += 1
                    if not target_metric and not target_type_name:
                        stats["no_mapping_found"] += 1
            
            # 4. 显示更新统计
            print("4. 更新统计:")
            print(f"   总记录数: {stats['total']}")
            print(f"   无需更新: {stats['no_update_needed']}")
            print(f"   需要更新 metric: {stats['update_metric']}")
            print(f"   需要更新 type_name: {stats['update_type_name']}")
            print(f"   需要更新两者: {stats['update_both']}")
            print(f"   使用 sensor_type 映射: {stats['use_sensor_type']}")
            print(f"   未找到映射: {stats['no_mapping_found']}")
            print()
            
            if not updates_needed:
                print("✓ 所有记录的映射关系都是正确的，无需更新")
                return True
            
            # 5. 显示前10条将要更新的记录（示例）
            print("5. 更新示例（前10条）:")
            print(f"{'ID':<8} {'当前 metric':<20} {'当前 type_name':<30} {'目标 metric':<20} {'目标 type_name':<30} {'原因'}")
            print("-" * 130)
            for update in updates_needed[:10]:
                print(f"{update['id']:<8} "
                      f"{update['current_metric'] or 'NULL':<20} "
                      f"{update['current_type_name'] or 'NULL':<30} "
                      f"{update['target_metric'] or 'NULL':<20} "
                      f"{update['target_type_name'] or 'NULL':<30} "
                      f"{update['reason']}")
            
            if len(updates_needed) > 10:
                print(f"   ... 还有 {len(updates_needed) - 10} 条记录")
            print()
            
            # 6. 执行更新
            if dry_run:
                print("⚠  DRY RUN 模式：跳过实际更新")
                print(f"   如果执行，将更新 {len(updates_needed)} 条记录")
            else:
                print(f"6. 开始更新 {len(updates_needed)} 条记录...")
                updated_count = 0
                
                for update in updates_needed:
                    set_clauses = []
                    params = {"id": update["id"]}
                    
                    if "metric" in update["update_fields"]:
                        set_clauses.append("metric = :metric")
                        params["metric"] = update["target_metric"]
                    
                    if "type_name" in update["update_fields"]:
                        set_clauses.append("type_name = :type_name")
                        params["type_name"] = update["target_type_name"]
                    
                    if set_clauses:
                        update_sql = f"""
                            UPDATE sensor_readings 
                            SET {', '.join(set_clauses)}
                            WHERE id = :id
                        """
                        session.execute(text(update_sql), params)
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            print(f"   已更新 {updated_count}/{len(updates_needed)} 条记录...")
                
                session.commit()
                print(f"✓ 成功更新 {updated_count} 条记录")
            
            print()
            print("=" * 60)
            print("✓ 更新完成")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"✗ 更新失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新 sensor_readings 表的 metric 和 type_name 映射关系")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要更新的数据，不实际更新")
    parser.add_argument("--limit", type=int, help="限制更新的记录数量（用于测试）")
    
    args = parser.parse_args()
    
    success = update_sensor_readings_mapping(dry_run=args.dry_run, limit=args.limit)
    
    if not success:
        sys.exit(1)


