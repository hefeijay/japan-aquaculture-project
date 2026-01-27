#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 客户端测试脚本 - 简化版
"""
import asyncio
import websockets
import json
import time


async def test_websocket():
    """测试 WebSocket 连接"""
    uri = "ws://localhost:8000/ws"  # 使用 /ws 路径
    
    print("=" * 80)
    print(f"🔌 连接到: {uri}")
    print("=" * 80)
    
    # 测试消息列表
    test_messages = [
        "帮我给AI2喂食1份",
        "查询1号池的水温数据",
        "查询AI2最近的喂食数据，然后帮我喂食1份"
    ]
    
    for idx, msg_text in enumerate(test_messages, 1):
        # 每次测试都创建新的 session_id
        session_id = f"test-{int(time.time())}-{idx}"
        
        print("\n" + "=" * 80)
        print(f"测试 {idx}/{len(test_messages)}: {msg_text}")
        print(f"📝 Session ID: {session_id}")
        print("=" * 80)
        
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ WebSocket 连接成功")
                
                # 1. 发送初始化消息
                init_msg = {
                    "type": "init",
                    "data": {
                        "session_id": session_id,
                        "user_id": "test_user"
                    }
                }
                await websocket.send(json.dumps(init_msg))
                print("📤 已发送初始化消息")
                
                # 接收初始化响应
                response = await websocket.recv()
                resp_data = json.loads(response)
                print(f"📨 收到初始化响应: {resp_data.get('type')}\n")
                
                # 2. 发送测试消息
                user_msg = {
                    "type": "userSendMessage",
                    "data": {
                        "content": msg_text,
                        "session_id": session_id,
                        "type": "text"
                    }
                }
                
                await websocket.send(json.dumps(user_msg))
                print("📤 消息已发送，等待响应...\n")
                
                # 收集完整响应
                assistant_content = ""
                message_count = 0
                start_time = time.time()
                
                try:
                    while message_count < 100:
                        response = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        message_count += 1
                        resp_data = json.loads(response)
                        msg_type = resp_data.get("type")
                        
                        # 收集流式内容
                        if msg_type == "stream_chunk":
                            data = resp_data.get("data", {})
                            event = data.get("event")
                            content = data.get("content", "")
                            
                            if event == "content" and content:
                                assistant_content += content
                            elif event == "end":
                                # 流式结束，输出完整内容
                                elapsed = time.time() - start_time
                                print(f"✅ 收到完整回复（耗时 {elapsed:.2f}秒）：")
                                print("-" * 80)
                                print(assistant_content)
                                print("-" * 80)
                                print(f"📊 共收到 {message_count} 条消息")
                                break
                
                except asyncio.TimeoutError:
                    print(f"⏱️ 超时（60秒），已收到部分内容：")
                    if assistant_content:
                        print("-" * 80)
                        print(assistant_content)
                        print("-" * 80)
        
        except websockets.exceptions.ConnectionClosed as e:
            print(f"❌ 连接关闭: {e}")
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        
        # 等待一下再进行下一个测试
        await asyncio.sleep(1)
    
    print("\n" + "=" * 80)
    print("🎉 所有测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    print("\n🤖 WebSocket 客户端测试脚本")
    print("=" * 80)
    
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
