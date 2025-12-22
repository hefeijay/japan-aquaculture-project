#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器数据处理器
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .base_handler import BaseHandler
from models.sensor_reading import SensorReading, QualityFlag

logger = logging.getLogger(__name__)


class SensorHandler(BaseHandler):
    """传感器数据处理处理器"""
    
    async def handle(
        self,
        orchestrator,
        state: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理传感器数据
        
        流程：
        1. 验证数据
        2. 清洗数据
        3. 保存到数据库
        4. 可选：AI 分析
        """
        try:
            input_data = state.get("cleaned_data") or state.get("input_data", {})
            
            # 1. 数据验证
            validation_result = self._validate_sensor_data(input_data)
            state["validation_result"] = validation_result
            
            if not validation_result.get("valid", False):
                state["error"] = "; ".join(validation_result.get("errors", []))
                state["should_continue"] = False
                return state
            
            # 2. 数据清洗
            cleaned = self._clean_sensor_data(input_data)
            state["cleaned_data"] = cleaned
            
            # 3. 保存到数据库
            from database import get_db
            with get_db() as db:
                reading = SensorReading(**cleaned)
                db.add(reading)
                db.flush()
                
                state["db_result"] = {
                    "id": reading.id,
                    "status": "saved",
                    "device_id": reading.device_id,
                    "metric": reading.metric,
                }
            
            # 4. 可选：AI 分析（由工作流节点处理，这里跳过）
            # AI 分析将在工作流的 ai_analysis 节点中处理
            
            state["nodes_completed"].append("sensor_handler")
            state["should_continue"] = True
            
            logger.info(f"传感器数据处理完成: {state['db_result']}")
            
        except Exception as e:
            logger.error(f"传感器数据处理失败: {e}", exc_info=True)
            state["error"] = str(e)
            state["should_continue"] = False
        
        return state
    
    def _validate_sensor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证传感器数据"""
        errors = []
        warnings = []
        
        # 检查必填字段
        required_fields = ["device_id", "metric", "value", "ts_utc"]
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")
        
        # 验证指标值范围
        if "metric" in data and "value" in data:
            metric = data["metric"]
            try:
                value = float(data["value"])
                
                thresholds = {
                    "do": (0, 20),  # 溶解氧 mg/L
                    "ph": (6.5, 9.0),
                    "temp": (15, 35),  # 水温 °C
                    "ammonia": (0, 0.5),  # 氨氮 mg/L
                    "nitrite": (0, 0.1),  # 亚硝酸盐 mg/L
                }
                
                if metric in thresholds:
                    min_val, max_val = thresholds[metric]
                    if value < min_val or value > max_val:
                        warnings.append(f"{metric} 值 {value} 超出正常范围 [{min_val}, {max_val}]")
            except (ValueError, TypeError):
                errors.append(f"无效的数值: {data.get('value')}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def _clean_sensor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗传感器数据"""
        cleaned = data.copy()
        
        # 时间标准化
        if "ts_utc" in cleaned and isinstance(cleaned["ts_utc"], str):
            try:
                cleaned["ts_utc"] = datetime.fromisoformat(cleaned["ts_utc"].replace("Z", "+00:00"))
            except:
                cleaned["ts_utc"] = datetime.utcnow()
        
        # 数值类型转换
        if "value" in cleaned:
            try:
                cleaned["value"] = float(cleaned["value"])
            except:
                pass
        
        # 设置质量标记
        if "quality_flag" not in cleaned:
            cleaned["quality_flag"] = QualityFlag.OK
        
        return cleaned
    
    async def _analyze_sensor_data(
        self,
        orchestrator,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 AI 分析传感器数据"""
        try:
            from agents.thinking_agent import ThinkingAgent
            
            thinking_agent = ThinkingAgent()
            
            context = {
                "data_type": "sensor",
                "metric": data.get("metric"),
                "value": data.get("value"),
                "unit": data.get("unit"),
            }
            
            user_input = f"请分析这个传感器读数：{data.get('metric')} = {data.get('value')} {data.get('unit', '')}"
            
            analysis, stats = await thinking_agent.think(
                user_input=user_input,
                context=context,
            )
            
            return {
                "analysis": analysis,
                "stats": stats,
            }
            
        except Exception as e:
            logger.error(f"AI 分析失败: {e}", exc_info=True)
            return {"error": str(e)}

