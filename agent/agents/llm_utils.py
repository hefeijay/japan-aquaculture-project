#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 工具函数 - 使用原生OpenAI API启用搜索功能
参考 cognitive_model/agents/llm_utils.py
"""
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable, Union
from openai import AsyncOpenAI  # 使用异步OpenAI客户端
from openai.types.chat import ChatCompletionMessageParam
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import settings

logger = logging.getLogger(__name__)

class LLMConfig:
    """LLM 配置类 - 支持搜索功能"""
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        enable_search: Optional[bool] = None,  # 是否启用搜索（None=自动根据配置）
        search_options: Optional[Dict] = None  # 搜索选项配置
    ):
        # 如果未指定，根据全局配置决定
        self.enable_search = enable_search if enable_search is not None else settings.ENABLE_LLM_SEARCH
        
        # 根据 enable_search 决定使用哪个模型
        if model:
            # 显式指定模型，直接使用
            self.model = model
        elif self.enable_search is True:
            # 启用搜索，使用搜索模型
            self.model = settings.OPENAI_SEARCH_MODEL
        elif self.enable_search is False:
            # 禁用搜索，使用基础模型
            self.model = settings.OPENAI_BASE_MODEL
            # print(f"🔧 禁用搜索，使用基础模型: {self.model}")
        else:
            # 未指定，使用默认模型
            self.model = settings.OPENAI_MODEL
        
        self.temperature = temperature or settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens
        self.search_options = search_options or {}

def _convert_to_openai_format(messages: Union[List, List[ChatCompletionMessageParam]]) -> List[ChatCompletionMessageParam]:
    """
    将LangChain消息或字典消息转换为OpenAI API格式
    支持混合输入格式
    """
    openai_messages: List[ChatCompletionMessageParam] = []
    
    for msg in messages:
        # 如果已经是字典格式，直接使用
        if isinstance(msg, dict):
            openai_messages.append(msg)  # type: ignore
        # 如果是 LangChain 消息对象
        elif hasattr(msg, 'content'):
            if isinstance(msg, SystemMessage):
                openai_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                openai_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                openai_messages.append({"role": "assistant", "content": msg.content})
            else:
                # 其他类型，尝试从 type 属性获取
                role = getattr(msg, 'type', 'user')
                if role == 'human':
                    role = 'user'
                elif role == 'ai':
                    role = 'assistant'
                openai_messages.append({"role": role, "content": msg.content})  # type: ignore
    
    return openai_messages


def format_messages_for_llm(
    system_prompt: str,
    history: Optional[List[Dict[str, str]]] = None
) -> List:
    """
    格式化消息为 LangChain 格式（保持向后兼容）
    返回 LangChain 消息对象列表
    """
    messages = [SystemMessage(content=system_prompt)]
    
    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
    
    return messages

def format_config_for_llm(model_config: Optional[Dict[str, Any]] = None) -> LLMConfig:
    """格式化 LLM 配置"""
    if model_config:
        return LLMConfig(
            model=model_config.get("model_name"),
            temperature=model_config.get("temperature"),
            max_tokens=model_config.get("max_tokens"),
            enable_search=model_config.get("enable_search"),  # None 会使用全局配置
            search_options=model_config.get("search_options")
        )
    return LLMConfig()

async def execute_llm_call(
    messages: Union[List, List[ChatCompletionMessageParam]],
    config: Optional[LLMConfig] = None,
    stream: bool = False,
    stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> tuple[str, Dict[str, Any]]:
    """
    执行 LLM 调用 - 使用原生OpenAI API并支持搜索
    兼容 LangChain 消息格式和 OpenAI 字典格式
    
    Args:
        messages: 消息列表（支持 LangChain 格式或 OpenAI 格式）
        config: LLM 配置
        stream: 是否流式返回
        stream_callback: 流式回调函数
        
    Returns:
        tuple: (response_content, stats_dict)
    """
    config = config or LLMConfig()
    
    # 初始化异步OpenAI客户端
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )
    
    try:
        # 自动转换消息格式为 OpenAI API 格式
        openai_messages = _convert_to_openai_format(messages)
        
        # 准备API调用参数
        api_params: Dict[str, Any] = {
            "model": config.model,
            "messages": openai_messages,
            "temperature": config.temperature,
        }
        
        # 只在有值时添加 max_tokens
        if config.max_tokens:
            api_params["max_tokens"] = config.max_tokens
        
        # 如果启用搜索，可以添加搜索选项（如果API支持）
        if config.enable_search:
            if config.search_options:
                api_params["extra"] = config.search_options
            # print(f"🔍 使用搜索模型: {config.model}")
        
        if stream:
            # 异步流式调用
            chunks = []
            stream_response = await client.chat.completions.create(
                **api_params,
                stream=True
            )
            
            async for chunk in stream_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                    chunks.append(chunk_content)
                    if stream_callback:
                        await stream_callback(chunk_content)
            
            response_content = "".join(chunks)
        else:
            # 非流式调用
            response = await client.chat.completions.create(**api_params)
            response_content = response.choices[0].message.content or ""
        
        # 统计信息
        stats = {
            "model": config.model,
            "enable_search": config.enable_search,
            "is_search_model": config.enable_search,  # 与 enable_search 保持一致
            "response_length": len(response_content)
        }
        
        return response_content, stats
        
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}", exc_info=True)
        raise

# 新增：专门用于搜索的便捷函数
async def execute_search_call(
    query: str,
    system_prompt: str = "你是一个有帮助的助手，请基于网络搜索提供准确、及时的信息。",
    search_options: Optional[Dict] = None,
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> tuple[str, Dict[str, Any]]:
    """
    执行带有联网搜索的 LLM 调用
    
    Args:
        query: 搜索查询
        system_prompt: 系统提示词
        search_options: 搜索选项配置
        temperature: 温度参数（默认 0.3，更精确）
        max_tokens: 最大 token 数（默认 2000）
        
    Returns:
        tuple: (response_content, stats_dict)
    """
    config = LLMConfig(
        model="gpt-4o-search-preview",  # 使用搜索模型
        enable_search=True,
        search_options=search_options,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    messages = format_messages_for_llm(system_prompt, [])
    messages.append(HumanMessage(content=query))
    
    return await execute_llm_call(messages, config)