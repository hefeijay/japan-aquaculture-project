#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部日本养殖专家咨询服务
参考: /usr/henry/cognitive-center/cognitive_model/tools/tools.json
"""
import logging
import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class ExpertConsultationService:
    """
    外部日本养殖专家咨询服务
    
    负责将重写后的问题发送给外部专家系统，获取专业建议
    使用SSE (Server-Sent Events) 流式API
    """
    
    def __init__(self):
        """初始化专家咨询服务"""
        # 默认使用参考配置中的地址
        self.base_url = settings.EXPERT_API_BASE_URL or "http://localhost:5003"
        self.api_key = settings.EXPERT_API_KEY
        self.timeout = settings.EXPERT_API_TIMEOUT
        self.agent_type = "japan"  # 固定为 "japan"，参考 tools.json
        
    async def consult(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        咨询外部专家（SSE流式API）
        
        Args:
            query: 重写后的查询问题
            context: 上下文信息（可选）
            session_id: 会话ID（必需）
            config: LLM配置（可选）
            
        Returns:
            Dict: 专家回复，包含 answer, confidence, sources 等字段
        """
        if not session_id:
            logger.warning("会话ID未提供，跳过专家咨询")
            return {
                "success": False,
                "error": "会话ID未提供",
                "answer": None,
            }
        
        try:
            # 构建请求参数（GET请求，使用查询参数）
            params = {
                "query": query,
                "agent_type": self.agent_type,  # 固定为 "japan"
                "session_id": session_id,
            }
            
            # 如果提供了config，将其序列化为JSON字符串
            if config:
                params["config"] = json.dumps(config, ensure_ascii=False)
            
            # 构建请求头
            headers = {
                "Accept": "text/event-stream",  # SSE流式响应
                "User-Agent": "Japan-Aquaculture-Backend/1.0",
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # 发送GET请求（SSE流式）
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"咨询外部专家 (SSE): {query[:50]}...")
                
                # 使用GET请求，实际端点为 /chat/stream
                url = f"{self.base_url}/chat/stream"
                
                async with client.stream(
                    "GET",
                    url,
                    params=params,
                    headers=headers,
                ) as response:
                    # 对于流式响应，先检查状态码，避免直接调用 raise_for_status()
                    if response.status_code != 200:
                        # 对于非200状态码，尝试读取错误信息
                        error_text = ""
                        try:
                            # 读取错误响应内容
                            async for chunk in response.aiter_bytes():
                                error_text += chunk.decode('utf-8', errors='ignore')
                                if len(error_text) > 1000:  # 限制读取长度
                                    break
                        except Exception:
                            pass
                        
                        error_msg = f"HTTP {response.status_code}"
                        if error_text:
                            error_msg = f"{error_msg}: {error_text[:200]}"
                        
                        logger.error(f"专家咨询HTTP错误: {error_msg}")
                        return {
                            "success": False,
                            "error": f"HTTP错误: {response.status_code}",
                            "answer": None,
                        }
                    
                    # 读取SSE流式响应
                    answer_parts = []
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # SSE格式: "data: {json}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            try:
                                data = json.loads(data_str)
                                # 收集答案片段
                                if "content" in data or "text" in data or "answer" in data:
                                    content = data.get("content") or data.get("text") or data.get("answer", "")
                                    if content:
                                        answer_parts.append(content)
                                # 检查是否完成
                                if data.get("done", False) or data.get("finished", False):
                                    break
                            except json.JSONDecodeError:
                                # 如果不是JSON，可能是纯文本
                                if data_str.strip():
                                    answer_parts.append(data_str)
                        elif line.startswith("event: "):
                            # 处理事件类型
                            event_type = line[7:].strip()
                            logger.debug(f"SSE事件: {event_type}")
                        else:
                            # 其他行，可能是纯文本内容
                            if line.strip():
                                answer_parts.append(line.strip())
                    
                    # 合并所有答案片段
                    answer = "".join(answer_parts)
                    
                    if answer:
                        logger.info(f"专家咨询成功: {answer[:50]}...")
                        return {
                            "success": True,
                            "answer": answer,
                            "confidence": 1.0,  # SSE流式响应没有置信度，设为1.0
                            "sources": [],  # SSE流式响应没有来源信息
                            "metadata": {
                                "agent_type": self.agent_type,
                                "session_id": session_id,
                                "response_type": "sse_stream",
                            },
                        }
                    else:
                        logger.warning("专家咨询返回空答案")
                        return {
                            "success": False,
                            "error": "专家咨询返回空答案",
                            "answer": None,
                        }
                
        except httpx.TimeoutException:
            logger.error(f"专家咨询超时: {query[:50]}...")
            return {
                "success": False,
                "error": "专家咨询超时",
                "answer": None,
            }
        except httpx.HTTPStatusError as e:
            # 对于流式响应，不能直接访问 .text，需要先读取
            error_detail = f"HTTP {e.response.status_code}"
            logger.error(f"专家咨询HTTP错误: {error_detail}")
            return {
                "success": False,
                "error": f"HTTP错误: {e.response.status_code}",
                "answer": None,
            }
        except Exception as e:
            logger.error(f"专家咨询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": None,
            }
    
    async def batch_consult(
        self,
        queries: list[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> list[Dict[str, Any]]:
        """
        批量咨询外部专家
        
        Args:
            queries: 查询问题列表
            context: 上下文信息（可选）
            
        Returns:
            List[Dict]: 专家回复列表
        """
        results = []
        for query in queries:
            result = await self.consult(query, context)
            results.append(result)
        return results


# 创建全局实例
expert_service = ExpertConsultationService()

