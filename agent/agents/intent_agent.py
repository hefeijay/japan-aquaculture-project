#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图识别智能体 - 参考 cognitive_model/agents/intent_agent.py
"""
import logging
from typing import Dict, Any, Tuple, List, Optional

from .llm_utils import execute_llm_call, LLMConfig, format_messages_for_llm, format_config_for_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class IntentAgent:
    """
    意图识别智能体
    
    负责分析用户输入，识别核心意图（如：数据查询、数据分析、设备控制等）
    """
    
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
    
    def __init__(self):
        """初始化意图识别智能体"""
        pass
    
    async def get_intent(
        self,
        user_input: str,
        history: Optional[List[Dict[str, str]]] = None,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入
            history: 对话历史
            model_config: 模型配置
            
        Returns:
            tuple: (意图字符串, 统计信息)
        """
        system_prompt = f"""你是一个意图识别专家。请分析用户输入，识别其核心意图。

有效的意图类型：
{', '.join(self.VALID_INTENTS)}

请只返回意图类型，不要返回其他内容。如果无法确定，返回"其他"。

示例：
- "查询1号池的水温数据" -> 数据查询
- "分析最近一周的溶解氧趋势" -> 数据分析
- "记录投食量500克" -> 数据录入
- "启动增氧设备" -> 设备控制
"""
        
        config = format_config_for_llm(model_config)
        messages = format_messages_for_llm(system_prompt, history or [])
        messages.append(HumanMessage(content=user_input))
        
        try:
            response_content, stats = await execute_llm_call(messages, config)
            
            # 清洗响应
            intent = response_content.strip().strip('"').strip("'")
            
            # 验证意图有效性
            if intent not in self.VALID_INTENTS:
                logger.warning(f"识别到无效意图: {intent}，使用默认意图'其他'")
                intent = "其他"
            
            logger.info(f"识别意图: {intent}")
            return intent, stats
            
        except Exception as e:
            logger.error(f"意图识别失败: {e}", exc_info=True)
            return "其他", {"error": str(e)}

