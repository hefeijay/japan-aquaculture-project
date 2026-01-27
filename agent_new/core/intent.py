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
        
        # ⚠️ 构建消息 - 意图识别不传入历史对话，避免 LLM 误以为需要对话
        messages = format_messages(
            system_prompt=system_prompt,
            user_message=query,
            history=None,  # 意图识别只基于当前输入
        )
        
        # 调用 LLM（意图识别使用较低温度）
        response = await llm_manager.invoke(
            messages=messages,
            temperature=0.1,  # 降低温度，提高确定性
        )
        
        # 清洗响应
        intent = response.strip().strip('"').strip("'").strip("。").strip("，")
        
        # 🔥 增强：从响应中提取有效意图（处理 LLM 返回完整句子的情况）
        if intent not in VALID_INTENTS:
            # 尝试从响应中查找有效意图关键词
            for valid_intent in VALID_INTENTS:
                if valid_intent in intent:
                    logger.info(f"从响应中提取意图: {response[:30]}... → {valid_intent}")
                    intent = valid_intent
                    break
            
            # 如果仍然无效，默认为"其他"
            if intent not in VALID_INTENTS:
                logger.warning(f"无效意图: {response[:50]}... → 其他")
                intent = "其他"
        
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

