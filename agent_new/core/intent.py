#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别模块
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

from prompts import load_prompt
from core.llm import llm_manager, format_messages

logger = logging.getLogger(__name__)

# 有效的意图列表
VALID_INTENTS = [
    "数据查询",
    "数据分析",
    "数据录入",
    "设备控制",
    "报告生成",
    "异常检测",
    "其他",
]

# 需要调用专家的意图
EXPERT_INTENTS = ["数据查询", "统计分析", "历史记录", "数据分析"]


async def recognize_intent(
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    识别用户意图
    
    Args:
        query: 用户输入
        history: 对话历史
        
    Returns:
        Tuple[str, Dict]: (意图, 统计信息)
    """
    try:
        # 加载意图识别提示词
        system_prompt = load_prompt("intent")
        
        # 构建消息
        messages = format_messages(
            system_prompt=system_prompt,
            user_message=query,
            history=history,
        )
        
        # 调用 LLM（意图识别使用较低温度）
        response = await llm_manager.invoke(
            messages=messages,
            temperature=0.3,
        )
        
        # 清洗响应
        intent = response.strip().strip('"').strip("'")
        
        # 验证意图有效性
        if intent not in VALID_INTENTS:
            logger.warning(f"无效意图: {intent} → 其他")
            intent = "其他"
        
        # ⭐️ 安全验证：定时任务相关的强制归为设备控制
        task_keywords = ["定时任务", "定时计划", "任务管理", "创建任务", "查看任务", "修改任务", "取消任务", "任务列表", "喂食计划"]
        if any(kw in query for kw in task_keywords):
            if intent != "设备控制":
                logger.info(f"意图修正: {intent} → 设备控制")
                intent = "设备控制"
        
        return intent, {"model": llm_manager.default_model}
        
    except Exception as e:
        logger.error(f"意图识别失败: {e}", exc_info=True)
        return "其他", {"error": str(e)}


def needs_expert(intent: str) -> bool:
    """
    判断意图是否需要调用专家
    
    Args:
        intent: 意图
        
    Returns:
        bool: 是否需要专家
    """
    if intent in EXPERT_INTENTS:
        return True
    if "数据" in intent or "查询" in intent or "分析" in intent:
        return True
    return False


def is_device_control(intent: str) -> bool:
    """
    判断是否为设备控制意图
    
    Args:
        intent: 意图
        
    Returns:
        bool: 是否为设备控制
    """
    return intent == "设备控制"


def is_casual_chat(intent: str) -> bool:
    """
    判断是否为闲聊
    
    Args:
        intent: 意图
        
    Returns:
        bool: 是否为闲聊
    """
    return intent == "其他"

