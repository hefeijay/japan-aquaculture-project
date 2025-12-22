#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础处理器 - 参考 cognitive_model/handlers/base_handler.py
"""
import abc
from typing import Dict, Any


class BaseHandler(abc.ABC):
    """
    所有数据处理器的基础类
    
    定义了统一的处理接口，确保所有处理器都能被工作流以相同的方式调用
    """
    
    @abc.abstractmethod
    async def handle(
        self,
        orchestrator,
        state: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理数据的核心抽象方法
        
        Args:
            orchestrator: 工作流协调器实例
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            dict: 更新后的状态
        """
        pass
    
    async def handle_stream(
        self,
        orchestrator,
        state: Dict[str, Any],
        stream_callback=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        流式处理版本（可选）
        
        默认实现调用普通 handle 方法
        """
        return await self.handle(orchestrator, state, **kwargs)

