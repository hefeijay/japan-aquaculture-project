#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联网搜索服务 - 使用 Serper API
"""
import logging
import aiohttp
from typing import Dict, Any, List

from config import settings

logger = logging.getLogger(__name__)

SERPER_API_URL = "https://google.serper.dev/search"


class WebSearchService:
    """Serper 联网搜索服务"""
    
    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        self.enabled = settings.ENABLE_WEB_SEARCH
        self.timeout = settings.WEB_SEARCH_TIMEOUT
    
    async def search(
        self,
        query: str,
        num_results: int = 5,
        language: str = "zh-CN",
    ) -> Dict[str, Any]:
        """
        执行联网搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            language: 语言
            
        Returns:
            Dict: 搜索结果，包含 success, results, error 字段
        """
        if not self.enabled:
            logger.debug("联网搜索未启用")
            return {"success": False, "results": [], "error": "搜索未启用"}
        
        if not self.api_key:
            logger.warning("Serper API Key 未配置")
            return {"success": False, "results": [], "error": "API Key 未配置"}
        
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "q": query,
                "num": num_results,
                "hl": language,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SERPER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_results(data)
                        logger.info(f"🔍 搜索完成: {query[:30]}... | 结果数: {len(results)}")
                        return {
                            "success": True,
                            "results": results,
                            "query": query,
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Serper API 错误: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "results": [],
                            "error": f"API 错误: {response.status}"
                        }
                        
        except aiohttp.ClientTimeout:
            logger.warning(f"搜索超时: {query[:30]}...")
            return {"success": False, "results": [], "error": "搜索超时"}
        except Exception as e:
            logger.error(f"搜索失败: {e}", exc_info=True)
            return {"success": False, "results": [], "error": str(e)}
    
    def _parse_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """解析 Serper 返回结果"""
        results = []
        
        # 解析 organic 结果
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
            })
        
        # 如果有 knowledge graph，也加入
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            results.insert(0, {
                "title": kg.get("title", ""),
                "snippet": kg.get("description", ""),
                "link": kg.get("website", ""),
                "type": "knowledge_graph"
            })
        
        return results
    
    def format_for_llm(self, search_result: Dict[str, Any]) -> str:
        """
        将搜索结果格式化为 LLM 可读的文本
        
        Args:
            search_result: search() 返回的结果
            
        Returns:
            str: 格式化后的文本，可直接用于 prompt
        """
        if not search_result.get("success") or not search_result.get("results"):
            return ""
        
        lines = ["【联网搜索结果】"]
        for i, item in enumerate(search_result["results"], 1):
            lines.append(f"\n{i}. {item['title']}")
            if item.get("snippet"):
                lines.append(f"   {item['snippet']}")
        
        return "\n".join(lines)


# 全局实例
web_search_service = WebSearchService()

