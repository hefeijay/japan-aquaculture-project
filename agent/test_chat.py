#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话功能测试脚本
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def test_chat(message: str, session_id: str = "test_session"):
    """测试对话接口"""
    print(f"\n{'='*60}")
    print(f"用户问题: {message}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={
                "message": message,
                "session_id": session_id,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ 响应成功")
            print(f"\n意图识别: {result.get('intent', 'N/A')}")
            print(f"\nAI 回答:")
            print("-" * 60)
            print(result.get('response', 'N/A'))
            print("-" * 60)
            
            if result.get('data_used'):
                print(f"\n使用的数据:")
                for data in result.get('data_used', []):
                    print(f"  - {data.get('type')}: {data.get('metric', 'N/A')}")
                    if 'readings' in data:
                        print(f"    共 {len(data['readings'])} 条记录")
            
            return result
        else:
            print(f"✗ 请求失败: {response.status_code}")
            print(f"  错误信息: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        print("  请确保服务已启动: uvicorn main:app --host 0.0.0.0 --port 8000")
        return None
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_health():
    """测试健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ 服务健康检查通过")
            return True
        else:
            print(f"✗ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到服务: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("日本陆上养殖数据处理系统 - 对话功能测试")
    print("=" * 60)
    
    # 1. 健康检查
    print("\n1. 检查服务状态...")
    if not test_health():
        print("\n请先启动服务:")
        print("  cd /srv/japan-aquaculture-project/backend")
        print("  ./start.sh")
        sys.exit(1)
    
    # 2. 测试对话
    print("\n2. 测试对话功能...")
    
    test_questions = [
        "你好，请介绍一下你自己",
        "查询最近的水温数据",
        "1号池的溶解氧是多少？",
        "分析一下pH值的变化趋势",
        "最近有哪些异常数据？",
    ]
    
    if len(sys.argv) > 1:
        # 如果提供了命令行参数，使用自定义问题
        test_questions = [" ".join(sys.argv[1:])]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n[测试 {i}/{len(test_questions)}]")
        result = test_chat(question, session_id=f"test_{i}")
        
        if result:
            print(f"\n✓ 测试 {i} 完成")
        else:
            print(f"\n✗ 测试 {i} 失败")
        
        # 等待一下，避免请求过快
        import time
        if i < len(test_questions):
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n提示:")
    print("  - 访问 http://localhost:8000/docs 查看完整 API 文档")
    print("  - 使用自定义问题: python test_chat.py '你的问题'")
    print("  - 查看日志了解详细处理过程")


if __name__ == "__main__":
    main()

