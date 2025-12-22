#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗服务
负责数据的时间标准化、单位统一、异常值检测等处理
"""

from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class DataCleaningService:
    """数据清洗服务类"""
    
    # 日本时区（UTC+9）
    JAPAN_TZ = timezone(offset=timedelta(hours=9))
    
    @staticmethod
    def standardize_time(ts: Any, timezone_offset: int = 9) -> Tuple[datetime, datetime]:
        """
        时间标准化：返回UTC和本地时间
        
        Args:
            ts: 时间戳（可以是datetime对象、Unix时间戳毫秒、字符串等）
            timezone_offset: 时区偏移（小时），默认9（日本时区）
            
        Returns:
            Tuple[datetime, datetime]: (UTC时间, 本地时间)
        """
        try:
            # 如果已经是datetime对象
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    # 假设是UTC时间
                    ts_utc = ts.replace(tzinfo=timezone.utc)
                else:
                    ts_utc = ts.astimezone(timezone.utc)
            # 如果是Unix时间戳（毫秒）
            elif isinstance(ts, (int, float)):
                if ts > 1e10:  # 毫秒时间戳
                    ts_utc = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                else:  # 秒时间戳
                    ts_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            # 如果是字符串
            elif isinstance(ts, str):
                # 尝试解析ISO格式
                try:
                    ts_utc = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if ts_utc.tzinfo is None:
                        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
                    else:
                        ts_utc = ts_utc.astimezone(timezone.utc)
                except ValueError:
                    # 回退到当前时间
                    ts_utc = datetime.now(timezone.utc)
            else:
                # 默认使用当前时间
                ts_utc = datetime.now(timezone.utc)
            
            # 转换为本地时间（日本时区）
            japan_tz = timezone(offset=timedelta(hours=timezone_offset))
            ts_local = ts_utc.astimezone(japan_tz)
            
            return ts_utc, ts_local
            
        except Exception as e:
            logger.error(f"时间标准化失败: {str(e)}")
            # 返回当前时间
            now_utc = datetime.now(timezone.utc)
            japan_tz = timezone(offset=timedelta(hours=timezone_offset))
            return now_utc, now_utc.astimezone(japan_tz)
    
    @staticmethod
    def normalize_unit(value: float, from_unit: str, to_unit: str) -> float:
        """
        单位统一转换
        
        Args:
            value: 原始值
            from_unit: 原始单位
            to_unit: 目标单位
            
        Returns:
            float: 转换后的值
        """
        # 单位转换表
        conversion_table = {
            # 长度单位
            ('mm', 'cm'): lambda x: x / 10,
            ('cm', 'mm'): lambda x: x * 10,
            ('m', 'cm'): lambda x: x * 100,
            ('cm', 'm'): lambda x: x / 100,
            # 重量单位
            ('g', 'kg'): lambda x: x / 1000,
            ('kg', 'g'): lambda x: x * 1000,
            # 温度单位（摄氏度保持不变）
            ('°C', '°C'): lambda x: x,
            ('C', '°C'): lambda x: x,
            # 其他单位保持不变
        }
        
        # 标准化单位名称
        from_unit_norm = from_unit.lower().strip()
        to_unit_norm = to_unit.lower().strip()
        
        # 如果单位相同，直接返回
        if from_unit_norm == to_unit_norm:
            return value
        
        # 查找转换函数
        key = (from_unit_norm, to_unit_norm)
        if key in conversion_table:
            return conversion_table[key](value)
        
        # 如果找不到转换规则，返回原值并记录警告
        logger.warning(f"未找到单位转换规则: {from_unit} -> {to_unit}")
        return value
    
    @staticmethod
    def detect_anomaly(value: float, metric: str, threshold: Optional[Dict[str, Any]] = None) -> bool:
        """
        异常值检测
        
        Args:
            value: 检测值
            metric: 指标名称（如：temperature, ph, do等）
            threshold: 阈值配置，格式：{"min": 最小值, "max": 最大值}
            
        Returns:
            bool: True表示异常，False表示正常
        """
        # 默认阈值配置（可根据实际情况调整）
        default_thresholds = {
            'temperature': {'min': 15.0, 'max': 35.0},
            'ph': {'min': 6.0, 'max': 9.0},
            'do': {'min': 3.0, 'max': 15.0},  # 溶解氧
            'dissolved_oxygen': {'min': 3.0, 'max': 15.0},
            'turbidity': {'min': 0.0, 'max': 100.0},
            'ammonia': {'min': 0.0, 'max': 2.0},
            'nitrite': {'min': 0.0, 'max': 0.5},
            'level': {'min': 0.5, 'max': 5.0},  # 水位（米）
            'light': {'min': 0.0, 'max': 10000.0},  # 光照强度
        }
        
        # 使用提供的阈值或默认阈值
        metric_lower = metric.lower()
        thresholds = threshold or default_thresholds.get(metric_lower, {})
        
        if not thresholds:
            # 如果没有阈值配置，返回False（不标记为异常）
            return False
        
        min_val = thresholds.get('min')
        max_val = thresholds.get('max')
        
        # 检查是否超出范围
        if min_val is not None and value < min_val:
            return True
        if max_val is not None and value > max_val:
            return True
        
        return False
    
    @staticmethod
    def generate_checksum(data: Dict[str, Any]) -> str:
        """
        生成完整性校验（checksum）
        
        Args:
            data: 数据字典
            
        Returns:
            str: MD5校验和（十六进制字符串）
        """
        try:
            # 将数据字典转换为字符串（排序键以确保一致性）
            data_str = str(sorted(data.items()))
            # 生成MD5校验和
            checksum = hashlib.md5(data_str.encode('utf-8')).hexdigest()
            return checksum
        except Exception as e:
            logger.error(f"生成校验和失败: {str(e)}")
            return ""
    
    @staticmethod
    def determine_quality_flag(
        value: Optional[float],
        metric: Optional[str],
        threshold: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        确定质量标记
        
        Args:
            value: 数据值
            metric: 指标名称
            threshold: 阈值配置
            
        Returns:
            str: 质量标记（'ok', 'missing', 'anomaly'）
        """
        # 检查是否缺失
        if value is None:
            return 'missing'
        
        # 检查是否异常
        if metric and DataCleaningService.detect_anomaly(value, metric, threshold):
            return 'anomaly'
        
        return 'ok'




