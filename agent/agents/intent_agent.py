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

⚠️ 【关键规则】
1. 只识别核心业务意图，不要识别天气、闲聊等辅助需求
2. 对于复合请求（如"先查天气再喂食"），识别其**主要操作意图**
3. 设备操作优先级最高：只要包含设备操作，必须返回"设备控制"

⚠️ 【设备控制优先级规则】
- 只要用户的请求中包含任何设备操作（喂食、投喂、打开、关闭、启动、停止、拍照、控制、调整等），
  无论是否还涉及数据查询、天气查询或其他内容，都必须判定为"设备控制"
- 设备控制包括但不限于：喂食机、摄像头、传感器、增氧机等设备的任何操作

✅ 有效的意图类型（必须且只能从以下选择一个）：
{', '.join(self.VALID_INTENTS)}

📝 示例（设备控制优先 - 即使有其他需求）：
- "查询AI2最近的喂食数据，然后帮我喂食1份" → 设备控制
- "打开1号喂食机" → 设备控制
- "给AI2投喂1份" → 设备控制
- "帮我拍张照片" → 设备控制
- "先看看水温，然后打开增氧机" → 设备控制
- "关闭2号摄像头" → 设备控制
- "查看一下今天天气，并给喂食机AI2喂食两份" → 设备控制
- "今天天气怎么样，然后帮我控制增氧机" → 设备控制

📝 示例（纯数据查询/分析 - 不涉及设备操作）：
- "查询1号池的水温数据" → 数据查询
- "分析最近一周的溶解氧趋势" → 数据分析
- "记录投食量500克" → 数据录入
- "生成本周水质报告" → 报告生成
- "检测异常数据" → 异常检测

📝 示例（闲聊、天气等 - 不涉及核心业务）：
- "你好" → 其他
- "今天天气怎么样" → 其他
- "你能做什么" → 其他

【严格输出要求】
你的回复必须且只能是上述意图类型中的一个词
禁止输出：
❌ 任何解释文字
❌ 任何标点符号（除了意图词本身）
❌ 任何Markdown格式（如 **, ##, |等）
❌ 任何emoji符号（如 ✅, 📊等）
❌ 任何表格或列表
❌ 多行内容
如果意图不在上述列表中，返回"其他"。
"""
        
        # 意图识别不需要搜索，显式禁用
        config = LLMConfig(
            model=model_config.get("model_name") if model_config else None,
            temperature=model_config.get("temperature") if model_config else None,
            max_tokens=model_config.get("max_tokens") if model_config else None,
            enable_search=False  # 意图识别禁用搜索
        )
        
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

