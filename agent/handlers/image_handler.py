#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像数据处理器
"""
import logging
from typing import Dict, Any
from datetime import datetime

from .base_handler import BaseHandler
from models.image_frame import ImageFrame
from models.image_detection import ImageDetection
from models.sensor_reading import QualityFlag

logger = logging.getLogger(__name__)


class ImageHandler(BaseHandler):
    """图像数据处理处理器"""
    
    async def handle(
        self,
        orchestrator,
        state: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """处理图像数据"""
        try:
            input_data = state.get("cleaned_data") or state.get("input_data", {})
            
            # 1. 数据验证
            validation_result = self._validate_image_data(input_data)
            state["validation_result"] = validation_result
            
            if not validation_result.get("valid", False):
                state["error"] = "; ".join(validation_result.get("errors", []))
                state["should_continue"] = False
                return state
            
            # 2. 数据清洗
            cleaned = self._clean_image_data(input_data)
            state["cleaned_data"] = cleaned
            
            # 3. 保存到数据库
            from database import get_db
            with get_db() as db:
                # 保存图像帧
                frame_data = {k: v for k, v in cleaned.items() if k != "detection"}
                frame = ImageFrame(**frame_data)
                db.add(frame)
                db.flush()
                
                # 如果有检测结果，也保存
                if "detection" in cleaned and cleaned["detection"]:
                    detection_data = cleaned["detection"].copy()
                    detection_data["frame_id"] = frame.id
                    detection_data["ts_utc"] = cleaned.get("ts_utc", datetime.utcnow())
                    detection = ImageDetection(**detection_data)
                    db.add(detection)
                    db.flush()
                    
                    state["db_result"] = {
                        "frame_id": frame.id,
                        "detection_id": detection.id,
                        "status": "saved",
                    }
                else:
                    state["db_result"] = {
                        "frame_id": frame.id,
                        "status": "saved",
                    }
            
            state["nodes_completed"].append("image_handler")
            state["should_continue"] = True
            
            logger.info(f"图像数据处理完成: {state['db_result']}")
            
        except Exception as e:
            logger.error(f"图像数据处理失败: {e}", exc_info=True)
            state["error"] = str(e)
            state["should_continue"] = False
        
        return state
    
    def _validate_image_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证图像数据"""
        errors = []
        warnings = []
        
        # 检查必填字段
        required_fields = ["camera_id", "ts_utc"]
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def _clean_image_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗图像数据"""
        cleaned = data.copy()
        
        # 时间标准化
        if "ts_utc" in cleaned and isinstance(cleaned["ts_utc"], str):
            try:
                cleaned["ts_utc"] = datetime.fromisoformat(cleaned["ts_utc"].replace("Z", "+00:00"))
            except:
                cleaned["ts_utc"] = datetime.utcnow()
        
        # 设置质量标记
        if "quality_flag" not in cleaned:
            cleaned["quality_flag"] = QualityFlag.OK
        
        return cleaned

