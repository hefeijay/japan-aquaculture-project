#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LLM 联网搜索功能 - 使用相同问题对比搜索效果
"""
import asyncio
from agents.llm_utils import execute_llm_call, execute_search_call, LLMConfig, format_messages_for_llm
from langchain_core.messages import HumanMessage

# 统一的测试问题（需要实时信息）
TEST_QUESTION = "今天（2026年1月15日）日本筑波的天气怎么样？气温多少度？"


async def test_search_model_with_convenience_function():
    """测试 1：使用便捷函数 + 搜索模型"""
    print("=" * 80)
    print("【测试 1】使用 execute_search_call 便捷函数（自动启用搜索）")
    print("=" * 80)
    print(f"📝 测试问题: {TEST_QUESTION}")
    
    try:
        response, stats = await execute_search_call(TEST_QUESTION)
        print(f"\n✅ 搜索成功")
        print(f"📊 统计信息: {stats}")
        print(f"🔍 是否使用搜索模型: {stats.get('is_search_model', False)}")
        print(f"\n💬 AI回复:\n{response}\n")
    except Exception as e:
        print(f"❌ 搜索失败: {e}\n")


async def test_search_model_manual_config():
    """测试 2：手动配置搜索模型"""
    print("=" * 80)
    print("【测试 2】手动配置 gpt-4o-search-preview（启用搜索）")
    print("=" * 80)
    
    try:
        # 创建配置，显式启用搜索
        config = LLMConfig(
            model="gpt-4o-search-preview",
            enable_search=True,
            temperature=0.3
        )
        
        # 构建消息
        messages = format_messages_for_llm(
            "你是一个有帮助的助手，请提供准确的信息。"
        )
        messages.append(HumanMessage(content=TEST_QUESTION))
        
        # 调用
        response, stats = await execute_llm_call(messages, config)
        print(f"\n✅ 调用成功")
        print(f"📊 统计信息: {stats}")
        print(f"🔍 是否使用搜索模型: {stats.get('is_search_model', False)}")
        print(f"\n💬 AI回复:\n{response}\n")
    except Exception as e:
        print(f"❌ 调用失败: {e}\n")


async def test_non_search_model():
    """测试 3：普通模型（对比组 - 无联网搜索）"""
    print("=" * 80)
    print("【测试 3】普通模型 gpt-4o（禁用搜索 - 对比组）")
    print("=" * 80)
    print(f"📝 测试问题: {TEST_QUESTION}")
    
    try:
        # 使用普通模型，禁用搜索
        config = LLMConfig(
            model="gpt-4o",
            enable_search=False,
            temperature=0.3  # 使用相同的 temperature
        )
        
        messages = format_messages_for_llm("你是一个有帮助的助手，请提供准确的信息。")
        messages.append(HumanMessage(content=TEST_QUESTION))
        
        response, stats = await execute_llm_call(messages, config)
        print(f"\n✅ 调用成功")
        print(f"📊 统计信息: {stats}")
        print(f"🔍 是否使用搜索模型: {stats.get('is_search_model', False)}")
        print(f"\n💬 AI回复:\n{response}\n")
        print("⚠️  注意：普通模型无法获取实时信息，可能会拒绝回答或提供过时信息")
    except Exception as e:
        print(f"❌ 调用失败: {e}\n")


async def main():
    print("\n" + "🔍" * 40)
    print("LLM 联网搜索功能对比测试")
    print("🔍" * 40 + "\n")
    
    print(f"📋 统一测试问题: {TEST_QUESTION}")
    print("🎯 目的: 对比有无搜索功能的模型响应差异\n")
    
    # 测试 1: 使用便捷函数（搜索模型）
    await test_search_model_with_convenience_function()
    
    await asyncio.sleep(2)
    
    # 测试 2: 手动配置（搜索模型）
    await test_search_model_manual_config()
    
    await asyncio.sleep(2)
    
    # 测试 3: 普通模型（对比组）
    await test_non_search_model()
    
    print("=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
    
    print("\n📊 预期结果对比:")
    print("  - 测试 1 & 2（搜索模型）：应该能够获取实时天气数据，给出准确的温度")
    print("  - 测试 3（普通模型）：   无法获取实时信息，可能拒绝回答或说明无法访问实时数据")
    
    print("\n💡 在项目中启用搜索功能:")
    print("  1. 在 .env 中设置 OPENAI_MODEL=gpt-4o-search-preview")
    print("  2. 在 .env 中设置 ENABLE_LLM_SEARCH=True")
    print("  3. 重启服务 python main.py")
    print("  4. 所有 LLM 调用将自动使用联网搜索功能")
    print("")


if __name__ == "__main__":
    asyncio.run(main())

