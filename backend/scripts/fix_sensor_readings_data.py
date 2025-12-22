#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器读数数据修复脚本

修复 sensor_readings 表中错误的字段映射：
1. metric='temperature' 但 type_name 错误的记录
2. metric='turbidity' 但 type_name 错误的记录
3. metric='ph' 但 type_name 错误的记录
4. 其他 metric 与 type_name 不匹配的记录

根据 sensor_id 和 metric 来确定正确的 type_name、unit 和 description
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 添加项目根目录的父目录到路径，使 japan_server 可以作为包导入
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
parent_dir = os.path.dirname(project_root)
# 将父目录添加到路径，这样 japan_server 才能作为包被导入
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# 同时将项目根目录也添加到路径（备用）
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from japan_server.db_models.db_session import db_session_factory
from japan_server.db_models.sensor_reading import SensorReading
from japan_server.db_models.sensor import Sensor
from japan_server.db_models.sensor_type import SensorType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fix_sensor_readings.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 传感器配置映射（根据客户端配置）
SENSOR_CONFIG_MAP = {
    1: {
        'name': '溶解氧传感器',
        'type': 'dissolved_oxygen',
        'metric': 'do',
        'unit': 'mg/L'
    },
    2: {
        'name': '液位传感器',
        'type': 'liquid_level',
        'metric': 'water_level',
        'unit': 'mm'
    },
    3: {
        'name': 'pH传感器',
        'type': 'ph',
        'metric': 'ph',
        'unit': 'pH'
    },
    4: {
        'name': '浊度传感器',
        'type': 'turbidity',
        'metric': 'turbidity',
        'unit': 'NTU'
    }
}

# metric 到正确配置的映射（用于温度字段的特殊处理）
METRIC_TO_CONFIG = {
    'do': {'name': '溶解氧传感器', 'unit': 'mg/L'},
    'water_level': {'name': '液位传感器', 'unit': 'mm'},
    'ph': {'name': 'pH传感器', 'unit': 'pH'},
    'turbidity': {'name': '浊度传感器', 'unit': 'NTU'},
    'temperature': None  # 需要根据 sensor_id 来确定
}


def get_correct_config_from_db(session, sensor_id: int, metric: str) -> Optional[Dict[str, str]]:
    """
    从数据库获取正确的配置
    
    Args:
        session: 数据库会话
        sensor_id: 传感器ID（sensor_readings 表中的 sensor_id，是外键）
        metric: 指标名称
        
    Returns:
        包含 type_name 和 unit 的字典，如果无法确定则返回 None
    """
    try:
        # 查询传感器及其类型信息
        sensor = session.query(Sensor).filter(Sensor.id == sensor_id).first()
        if not sensor:
            logger.warning(f"未找到 sensor_id={sensor_id} 的传感器记录")
            return None
        
        # 获取传感器类型信息
        sensor_type = sensor.sensor_type if hasattr(sensor, 'sensor_type') else None
        if not sensor_type:
            # 如果关系未加载，手动查询
            sensor_type = session.query(SensorType).filter(
                SensorType.id == sensor.sensor_type_id
            ).first()
        
        if not sensor_type:
            logger.warning(f"未找到 sensor_id={sensor_id} 的传感器类型信息")
            return None
        
        # 如果是温度字段，使用传感器的 type_name，但 unit 改为 '°C'
        if metric == 'temperature':
            return {
                'type_name': sensor_type.type_name,
                'unit': '°C'
            }
        
        # 普通字段，使用传感器类型的配置
        return {
            'type_name': sensor_type.type_name,
            'unit': sensor_type.unit or ''
        }
        
    except Exception as e:
        logger.error(f"获取配置失败: sensor_id={sensor_id}, metric={metric}, error={e}")
        return None


def get_correct_config(sensor_id: int, metric: str, session=None) -> Optional[Dict[str, str]]:
    """
    根据 sensor_id 和 metric 获取正确的配置（优先使用硬编码配置，因为数据库配置可能不正确）
    
    Args:
        sensor_id: 传感器ID
        metric: 指标名称
        session: 数据库会话（可选，用于日志记录）
        
    Returns:
        包含 type_name 和 unit 的字典，如果无法确定则返回 None
    """
    # 优先使用硬编码配置（因为数据库配置可能不正确）
    sensor_config = SENSOR_CONFIG_MAP.get(sensor_id)
    if not sensor_config:
        # 如果硬编码配置中没有，尝试从数据库获取（作为备用）
        if session:
            config = get_correct_config_from_db(session, sensor_id, metric)
            if config:
                logger.warning(f"sensor_id={sensor_id} 不在硬编码配置中，使用数据库配置")
                return config
        return None
    
    # 如果是温度字段，需要特殊处理
    if metric == 'temperature':
        return {
            'type_name': sensor_config['name'],
            'unit': '°C'
        }
    
    # 普通字段，检查 metric 是否匹配
    if metric == sensor_config['metric']:
        return {
            'type_name': sensor_config['name'],
            'unit': sensor_config['unit']
        }
    
    # 如果 metric 不匹配，尝试从 METRIC_TO_CONFIG 获取
    metric_config = METRIC_TO_CONFIG.get(metric)
    if metric_config and metric_config is not None:
        return metric_config
    
    return None


def get_correct_description(pool_id: Optional[str], metric: str, batch_id: Optional[int] = None) -> str:
    """
    生成正确的 description
    
    Args:
        pool_id: 池号
        metric: 指标名称
        batch_id: 批次ID（可选）
        
    Returns:
        描述字符串
    """
    pool_id = pool_id or "unknown"
    description = f"{pool_id}号池 - {metric}"
    if batch_id:
        description += f" - 批次{batch_id}"
    return description


def find_incorrect_records(session, dry_run: bool = True) -> List[Tuple[SensorReading, Dict[str, str]]]:
    """
    查找需要修复的记录
    
    Args:
        session: 数据库会话
        dry_run: 是否为干运行模式（只查找不修复）
        
    Returns:
        需要修复的记录列表，每个元素为 (SensorReading, 正确配置字典)
    """
    incorrect_records = []
    
    # 查询所有有 metric 的记录
    all_readings = session.query(SensorReading).filter(
        SensorReading.metric.isnot(None)
    ).all()
    
    logger.info(f"共找到 {len(all_readings)} 条有 metric 的记录")
    
    for reading in all_readings:
        sensor_id = reading.sensor_id
        metric = reading.metric
        
        # 从数据库获取正确的配置
        correct_config = get_correct_config(sensor_id, metric, session=session)
        if not correct_config:
            logger.warning(f"无法确定 sensor_id={sensor_id}, metric={metric} 的正确配置，跳过")
            continue
        
        # 检查是否需要修复
        needs_fix = False
        fixes = {}
        
        # 检查 type_name（包括 None 的情况）
        current_type_name = reading.type_name or ''
        correct_type_name = correct_config.get('type_name', '')
        if current_type_name != correct_type_name:
            needs_fix = True
            fixes['type_name'] = (reading.type_name, correct_type_name)
        
        # 检查 unit
        if reading.unit != correct_config['unit']:
            needs_fix = True
            fixes['unit'] = (reading.unit, correct_config['unit'])
        
        # 检查 description（如果 metric 或 pool_id 变化，description 可能需要更新）
        correct_description = get_correct_description(reading.pool_id, metric, reading.batch_id)
        if reading.description != correct_description:
            needs_fix = True
            fixes['description'] = (reading.description, correct_description)
        
        if needs_fix:
            incorrect_records.append((reading, correct_config, fixes))
            if dry_run:
                logger.info(
                    f"发现需要修复的记录 ID={reading.id}: "
                    f"sensor_id={sensor_id}, metric={metric}, "
                    f"fixes={fixes}"
                )
    
    return incorrect_records


def fix_records(session, records: List[Tuple[SensorReading, Dict[str, str], Dict]], dry_run: bool = True) -> Dict[str, int]:
    """
    修复记录
    
    Args:
        session: 数据库会话
        records: 需要修复的记录列表
        dry_run: 是否为干运行模式
        
    Returns:
        修复统计信息
    """
    stats = {
        'total': len(records),
        'fixed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    if dry_run:
        logger.info(f"[DRY-RUN] 将修复 {len(records)} 条记录")
        return stats
    
    for reading, correct_config, fixes in records:
        try:
            # 应用修复
            if 'type_name' in fixes:
                reading.type_name = fixes['type_name'][1]
                logger.debug(f"修复 ID={reading.id}: type_name {fixes['type_name'][0]} -> {fixes['type_name'][1]}")
            
            if 'unit' in fixes:
                reading.unit = fixes['unit'][1]
                logger.debug(f"修复 ID={reading.id}: unit {fixes['unit'][0]} -> {fixes['unit'][1]}")
            
            if 'description' in fixes:
                reading.description = fixes['description'][1]
                logger.debug(f"修复 ID={reading.id}: description {fixes['description'][0]} -> {fixes['description'][1]}")
            
            # 使用 merge 确保对象被正确管理
            session.merge(reading)
            stats['fixed'] += 1
            
            if stats['fixed'] % 100 == 0:
                session.flush()  # 先刷新到数据库
                session.commit()
                logger.info(f"已修复 {stats['fixed']} 条记录...")
                
        except Exception as e:
            logger.error(f"修复记录 ID={reading.id} 失败: {e}", exc_info=True)
            stats['failed'] += 1
            session.rollback()
    
    # 最终提交
    try:
        session.flush()  # 先刷新到数据库
        session.commit()
        logger.info(f"所有修复已提交，共修复 {stats['fixed']} 条记录")
    except Exception as e:
        logger.error(f"提交修复失败: {e}", exc_info=True)
        session.rollback()
        stats['failed'] += stats['fixed']
        stats['fixed'] = 0
    
    return stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='修复 sensor_readings 表中错误的字段映射',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 干运行模式（只查找不修复）
  python scripts/fix_sensor_readings_data.py --dry-run
  
  # 实际修复
  python scripts/fix_sensor_readings_data.py --execute
  
  # 只修复特定 sensor_id 的记录
  python scripts/fix_sensor_readings_data.py --execute --sensor-id 3
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='干运行模式（默认），只查找不修复'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='实际执行修复（需要明确指定）'
    )
    
    parser.add_argument(
        '--yes',
        action='store_true',
        help='跳过确认提示，直接执行修复'
    )
    
    parser.add_argument(
        '--sensor-id',
        type=int,
        default=None,
        help='只修复指定 sensor_id 的记录（可选）'
    )
    
    parser.add_argument(
        '--metric',
        type=str,
        default=None,
        help='只修复指定 metric 的记录（可选）'
    )
    
    args = parser.parse_args()
    
    # 确定是否为干运行模式
    dry_run = not args.execute
    
    if dry_run:
        logger.info("="*60)
        logger.info("干运行模式：只查找需要修复的记录，不实际修改")
        logger.info("="*60)
    else:
        logger.info("="*60)
        logger.info("执行模式：将实际修复数据库记录")
        logger.info("="*60)
        if not args.yes:
            try:
                response = input("确认要继续吗？(yes/no): ")
                if response.lower() != 'yes':
                    logger.info("用户取消操作")
                    return
            except (EOFError, KeyboardInterrupt):
                logger.error("无法获取用户输入，请使用 --yes 参数跳过确认")
                return
        else:
            logger.info("使用 --yes 参数，跳过确认提示")
    
    try:
        with db_session_factory() as session:
            # 查找需要修复的记录
            logger.info("开始查找需要修复的记录...")
            incorrect_records = find_incorrect_records(session, dry_run=dry_run)
            
            # 过滤记录（如果指定了 sensor_id 或 metric）
            if args.sensor_id:
                incorrect_records = [
                    (r, c, f) for r, c, f in incorrect_records
                    if r.sensor_id == args.sensor_id
                ]
                logger.info(f"过滤后，sensor_id={args.sensor_id} 的记录数: {len(incorrect_records)}")
            
            if args.metric:
                incorrect_records = [
                    (r, c, f) for r, c, f in incorrect_records
                    if r.metric == args.metric
                ]
                logger.info(f"过滤后，metric={args.metric} 的记录数: {len(incorrect_records)}")
            
            if not incorrect_records:
                logger.info("未找到需要修复的记录")
                return
            
            logger.info(f"共找到 {len(incorrect_records)} 条需要修复的记录")
            
            # 修复记录
            stats = fix_records(session, incorrect_records, dry_run=dry_run)
            
            # 打印统计信息
            logger.info("="*60)
            logger.info("修复完成统计")
            logger.info("="*60)
            logger.info(f"总记录数: {stats['total']}")
            logger.info(f"成功修复: {stats['fixed']}")
            logger.info(f"修复失败: {stats['failed']}")
            logger.info(f"跳过记录: {stats['skipped']}")
            logger.info("="*60)
            
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

