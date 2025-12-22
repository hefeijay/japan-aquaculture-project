#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 状态定义 - 参考 cognitive_model/orchestrator.py 的设计
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class AquacultureState(TypedDict):
    """养殖数据处理状态"""
    # 输入数据
    user_input: str
    session_id: str
    data_type: str  # sensor, image, feeder, operation, manual, history
    
    # 工作流状态
    current_node: str
    nodes_completed: List[str]
    error: Optional[str]
    
    # 意图识别结果
    intent: Optional[str]
    intent_confidence: Optional[float]
    
    # 数据验证结果
    validation_result: Optional[Dict[str, Any]]
    
    # 清洗后的数据
    cleaned_data: Optional[Dict[str, Any]]
    
    # 数据库操作结果
    db_result: Optional[Dict[str, Any]]
    
    # AI 分析结果
    ai_analysis: Optional[Dict[str, Any]]
    
    # 最终输出
    response: Optional[Dict[str, Any]]
    full_response: Optional[str]
    
    # 元数据
    batch_id: Optional[int]
    pool_id: Optional[str]
    device_id: Optional[int]
    timestamp: Optional[datetime]
    
    # 工作流控制
    should_continue: bool
    retry_count: int
