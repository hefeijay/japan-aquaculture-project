#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部设备控制专家咨询服务
"""
import logging
import httpx
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class DeviceExpertService:
    """
    外部设备控制专家咨询服务
    
    负责将设备控制请求发送给外部设备管理专家系统
    """
    
    def __init__(self):
        """初始化设备专家咨询服务"""
        self.base_url = settings.DEVICE_EXPERT_API_BASE_URL or "http://localhost:8000"
        self.timeout = settings.DEVICE_EXPERT_API_TIMEOUT
        
    async def consult(
        self,
        query: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        咨询外部设备专家（SSE流式，但同步返回最终结果）
        
        Args:
            query: 用户的设备控制请求
            session_id: 会话ID（必需）
            context: 上下文信息（可选）
            
        Returns:
            Dict: 设备专家回复，包含 success, result, device_type, error 等字段
        """
        if not session_id:
            logger.warning("会话ID未提供，跳过设备专家咨询")
            return {
                "success": False,
                "error": "会话ID未提供",
                "result": None,
            }
        
        try:
            # 构建请求参数（POST请求，JSON格式）
            payload = {
                "query": query,
                "session_id": session_id,
                "context": context or {}
            }
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",  # SSE流式响应
                "User-Agent": "Japan-Aquaculture-Agent/1.0",
            }
            
            # 发送POST请求（SSE流式）
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"咨询外部设备专家 (SSE): {query[:50]}...")
                
                # 使用POST请求，端点为 /api/v1/chat/stream
                url = f"{self.base_url}/api/v1/chat/stream"
                
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers,
                ) as response:
                    # 检查状态码
                    if response.status_code != 200:
                        error_text = ""
                        try:
                            async for chunk in response.aiter_bytes():
                                error_text += chunk.decode('utf-8', errors='ignore')
                                if len(error_text) > 1000:
                                    break
                        except Exception:
                            pass
                        
                        error_msg = f"HTTP {response.status_code}"
                        if error_text:
                            error_msg = f"{error_msg}: {error_text[:200]}"
                        
                        logger.error(f"设备专家咨询HTTP错误: {error_msg}")
                        return {
                            "success": False,
                            "error": f"HTTP错误: {response.status_code}",
                            "result": None,
                        }
                    
                    # 读取SSE流式响应
                    final_result = None
                    final_success = False
                    final_error = None
                    final_device_type = None
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # SSE格式: "data: {json}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                
                                # 处理不同类型的事件
                                if event_type == "start":
                                    logger.debug(f"设备专家流式开始: session_id={data.get('session_id')}")
                                
                                elif event_type == "node_update":
                                    node = data.get("node", "unknown")
                                    logger.debug(f"设备专家节点更新: {node}")
                                
                                elif event_type == "message":
                                    # 收到消息内容（流式中间过程，此处可忽略）
                                    content = data.get("content", "")
                                    logger.debug(f"设备专家消息片段: {content[:50]}...")
                                
                                elif event_type == "done":
                                    # 完成，保存最终结果
                                    final_success = data.get("success", False)
                                    final_result = data.get("result")
                                    final_error = data.get("error")
                                    final_device_type = data.get("device_type")
                                    logger.info(f"设备专家流式完成: success={final_success}, device_type={final_device_type}")
                                    break
                                
                                elif event_type == "error":
                                    # 错误事件
                                    final_error = data.get("error", "未知错误")
                                    logger.error(f"设备专家流式错误: {final_error}")
                                    break
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析SSE数据: {data_str[:100]}")
                    
                    # 返回最终结果
                    if final_success:
                        logger.info(f"设备专家咨询成功: device_type={final_device_type}")
                        return {
                            "success": True,
                            "result": final_result,
                            "device_type": final_device_type,
                            "session_id": session_id,
                            "metadata": {
                                "response_type": "sse_stream",
                            },
                        }
                    else:
                        logger.warning(f"设备专家咨询失败: {final_error}")
                        return {
                            "success": False,
                            "error": final_error or "设备操作失败",
                            "result": None,
                        }
                
        except httpx.TimeoutException:
            logger.error(f"设备专家咨询超时: {query[:50]}...")
            return {
                "success": False,
                "error": "设备专家咨询超时",
                "result": None,
            }
        except Exception as e:
            logger.error(f"设备专家咨询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None,
            }
    
    async def consult_stream(
        self,
        query: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        stream_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        咨询外部设备专家（流式）
        
        Args:
            query: 用户的设备控制请求
            session_id: 会话ID（必需）
            context: 上下文信息（可选）
            stream_callback: 流式回调函数，用于逐块发送消息
            
        Returns:
            Dict: 设备专家回复，包含 success, result, device_type, error 等字段
        """
        if not session_id:
            logger.warning("会话ID未提供，跳过设备专家咨询")
            return {
                "success": False,
                "error": "会话ID未提供",
                "result": None,
            }
        
        try:
            # 构建请求参数（POST请求，JSON格式）
            payload = {
                "query": query,
                "session_id": session_id,
                "context": context or {}
            }
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",  # SSE流式响应
                "User-Agent": "Japan-Aquaculture-Agent/1.0",
            }
            
            # 发送POST请求（流式）
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"咨询外部设备专家 (流式): {query[:50]}...")
                
                # 使用POST请求，端点为 /api/v1/chat/stream
                url = f"{self.base_url}/api/v1/chat/stream"
                
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers,
                ) as response:
                    # 检查状态码
                    if response.status_code != 200:
                        error_text = ""
                        try:
                            async for chunk in response.aiter_bytes():
                                error_text += chunk.decode('utf-8', errors='ignore')
                                if len(error_text) > 1000:
                                    break
                        except Exception:
                            pass
                        
                        error_msg = f"HTTP {response.status_code}"
                        if error_text:
                            error_msg = f"{error_msg}: {error_text[:200]}"
                        
                        logger.error(f"设备专家咨询HTTP错误: {error_msg}")
                        return {
                            "success": False,
                            "error": f"HTTP错误: {response.status_code}",
                            "result": None,
                        }
                    
                    # 读取SSE流式响应
                    final_result = None
                    final_success = False
                    final_error = None
                    final_device_type = None
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # SSE格式: "data: {json}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type")
                                
                                # 处理不同类型的事件
                                if event_type == "start":
                                    logger.debug(f"设备专家流式开始: session_id={data.get('session_id')}")
                                
                                elif event_type == "node_update":
                                    node = data.get("node", "unknown")
                                    logger.debug(f"设备专家节点更新: {node}")
                                
                                elif event_type == "message":
                                    # 收到消息内容，如果有回调则调用
                                    content = data.get("content", "")
                                    if content and stream_callback:
                                        await stream_callback(content)
                                
                                elif event_type == "done":
                                    # 完成，保存最终结果
                                    final_success = data.get("success", False)
                                    final_result = data.get("result")
                                    final_error = data.get("error")
                                    final_device_type = data.get("device_type")
                                    logger.info(f"设备专家流式完成: success={final_success}, device_type={final_device_type}")
                                    break
                                
                                elif event_type == "error":
                                    # 错误事件
                                    final_error = data.get("error", "未知错误")
                                    logger.error(f"设备专家流式错误: {final_error}")
                                    break
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"无法解析SSE数据: {data_str[:100]}")
                    
                    # 返回最终结果
                    if final_success:
                        return {
                            "success": True,
                            "result": final_result,
                            "device_type": final_device_type,
                            "session_id": session_id,
                            "metadata": {
                                "response_type": "sse_stream",
                            },
                        }
                    else:
                        return {
                            "success": False,
                            "error": final_error or "设备操作失败",
                            "result": None,
                        }
                
        except httpx.TimeoutException:
            logger.error(f"设备专家咨询超时: {query[:50]}...")
            return {
                "success": False,
                "error": "设备专家咨询超时",
                "result": None,
            }
        except Exception as e:
            logger.error(f"设备专家咨询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None,
            }


# 创建全局实例
device_expert_service = DeviceExpertService()

