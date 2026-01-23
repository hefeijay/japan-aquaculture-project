#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词模块 - 集中管理所有提示词
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """
    加载提示词文件
    
    Args:
        name: 提示词文件名（不含 .md 后缀）
        
    Returns:
        str: 提示词内容
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

