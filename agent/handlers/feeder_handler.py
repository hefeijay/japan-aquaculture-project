#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
喂食机数据处理器
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .base_handler import BaseHandler
from models.feeder_log import FeederLog

logger = logging.getLogger(__name__)


class FeederHandler(BaseHandler):
    """喂食机数据处理处理器"""
    
    async def handle(
        self,
        orchestrator,
        state: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """处理喂食机数据"""
        try:
            input_data = state.get("cleaned_data") or state.get("input_data", {})
            
            # 1. 数据验证
            validation_result = self._validate_feeder_data(input_data)
            state["validation_result"] = validation_result
            
            if not validation_result.get("valid", False):
                state["error"] = "; ".join(validation_result.get("errors", []))
                state["should_continue"] = False
                return state
            
            # 2. 数据清洗
            cleaned = self._clean_feeder_data(input_data)
            state["cleaned_data"] = cleaned
            
            # 3. 保存到数据库
            from database import get_db
            with get_db() as db:
                log = FeederLog(**cleaned)
                db.add(log)
                db.flush()
                
                state["db_result"] = {
                    "id": log.id,
                    "status": "saved",
                    "feeder_id": log.feeder_id,
                }
            
            state["nodes_completed"] = state.get("nodes_completed", [])
            state["nodes_completed"].append("feeder_handler")
            state["should_continue"] = True
            
            logger.info(f"喂食机数据处理完成: {state['db_result']}")
            
        except Exception as e:
            logger.error(f"喂食机数据处理失败: {e}", exc_info=True)
            state["error"] = str(e)
            state["should_continue"] = False
        
        return state
    
    def _validate_feeder_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证喂食机数据"""
        errors = []
        warnings = []
        
        # 检查必填字段
        required_fields = ["feeder_id", "ts_utc"]
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def _clean_feeder_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗喂食机数据"""
        cleaned = data.copy()
        
        # 时间标准化
        if "ts_utc" in cleaned and isinstance(cleaned["ts_utc"], str):
            try:
                cleaned["ts_utc"] = datetime.fromisoformat(cleaned["ts_utc"].replace("Z", "+00:00"))
            except:
                cleaned["ts_utc"] = datetime.utcnow()
        
        # 设置默认状态
        if "status" not in cleaned:
            cleaned["status"] = "ok"
        
        return cleaned

