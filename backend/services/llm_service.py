#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用大模型服务
统一封装 OpenAI 兼容接口调用，供预测等后续场景复用。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from config.settings import Config

logger = logging.getLogger(__name__)


class LLMService:
    """OpenAI 兼容大模型服务。"""

    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.base_url = Config.OPENAI_BASE_URL.rstrip("/")
        self.model = Config.OPENAI_MODEL
        self.temperature = Config.OPENAI_TEMPERATURE
        self.timeout = Config.OPENAI_TIMEOUT

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """调用 OpenAI 兼容的 chat completions 接口。"""
        if not self.is_enabled():
            raise RuntimeError("LLM 配置不完整，无法调用大模型")

        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("LLM 返回结果为空")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("LLM 返回内容为空")
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """调用模型并解析 JSON 返回。"""
        content = self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return self._extract_json(content)

    def _extract_json(self, content: str) -> Dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            parts = text.split("```")
            for part in parts:
                candidate = part.strip()
                if not candidate:
                    continue
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    return json.loads(candidate)
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError(f"无法从模型响应中解析 JSON: {text[:200]}")


llm_service = LLMService()
