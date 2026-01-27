#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LLM API 连接
验证不同的模型和 base_url 配置是否可用
"""
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取 API Key
OPENAI_API_KEY = "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"
OPENAI_BASE_URL = "https://openrouter.ai/api/v1"

print("=" * 80)
print("🔍 LLM API 连接测试")
print("=" * 80)
print(f"API Key: {OPENAI_API_KEY[:20]}..." if OPENAI_API_KEY else "❌ 未设置 OPENAI_API_KEY")
print(f"Base URL: {OPENAI_BASE_URL or '(默认 OpenAI API)'}")
print("=" * 80)

# 测试配置列表
test_configs = [
    {
        "name": "OpenAI GPT-4o",
        "base_url": None,
        "model": "gpt-4o",
    },
    {
        "name": "OpenAI GPT-4o-mini",
        "base_url": None,
        "model": "gpt-4o-mini",
    },
    {
        "name": "OpenAI GPT-3.5 Turbo",
        "base_url": None,
        "model": "gpt-3.5-turbo",
    },
    {
        "name": "OpenRouter Claude Sonnet 4.5",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4.5",
    },
    {
        "name": "OpenRouter GPT-4o",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o",
    },
    {
        "name": "当前环境变量配置",
        "base_url": OPENAI_BASE_URL,
        "model": os.getenv("OPENAI_BASE_MODEL", "gpt-4o"),
    },
]


async def test_llm_connection(config: dict) -> tuple[bool, str]:
    """
    测试 LLM 连接
    
    Returns:
        tuple: (是否成功, 响应内容或错误信息)
    """
    try:
        # 创建客户端
        client_kwargs = {
            "api_key": OPENAI_API_KEY,
        }
        if config["base_url"]:
            client_kwargs["base_url"] = config["base_url"]
        
        client = AsyncOpenAI(**client_kwargs)
        
        # 简单的测试消息
        messages = [
            {"role": "user", "content": "请用一句话介绍你自己"}
        ]
        
        # 调用 API
        response = await client.chat.completions.create(
            model=config["model"],
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )
        
        content = response.choices[0].message.content or ""
        return True, content
        
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            return False, f"❌ 403 错误: 模型在您的地区不可用或没有权限"
        elif "401" in error_msg:
            return False, f"❌ 401 错误: API Key 无效或未授权"
        elif "404" in error_msg:
            return False, f"❌ 404 错误: 模型不存在"
        else:
            return False, f"❌ 错误: {error_msg[:100]}"


async def main():
    """主测试函数"""
    print("\n开始测试各种配置...\n")
    
    success_count = 0
    fail_count = 0
    
    for i, config in enumerate(test_configs, 1):
        print(f"[{i}/{len(test_configs)}] 测试: {config['name']}")
        print(f"    模型: {config['model']}")
        print(f"    Base URL: {config['base_url'] or '(默认)'}")
        
        success, result = await test_llm_connection(config)
        
        if success:
            print(f"    ✅ 成功!")
            print(f"    响应: {result[:80]}...")
            success_count += 1
        else:
            print(f"    {result}")
            fail_count += 1
        
        print()
    
    print("=" * 80)
    print(f"测试完成: ✅ {success_count} 成功 | ❌ {fail_count} 失败")
    print("=" * 80)
    
    if success_count > 0:
        print("\n💡 建议:")
        print("   找到一个可用的配置后，更新您的 .env 文件:")
        print("   - OPENAI_BASE_URL=<base_url>")
        print("   - OPENAI_SEARCH_MODEL=<model>")
        print("   - OPENAI_BASE_MODEL=<model>")
        print("   - OPENAI_MODEL=<model>")
    else:
        print("\n⚠️ 所有配置都失败了，请检查:")
        print("   1. OPENAI_API_KEY 是否正确")
        print("   2. 是否有相应的 API 访问权限")
        print("   3. 网络连接是否正常")
        print("   4. 如果使用 OpenRouter，确保 API Key 来自 openrouter.ai")


if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("\n❌ 错误: 未找到 OPENAI_API_KEY")
        print("请在 .env 文件中设置 OPENAI_API_KEY")
        exit(1)
    
    asyncio.run(main())

