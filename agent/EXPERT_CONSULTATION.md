# 外部专家咨询服务说明

## 功能概述

系统现在支持将重写后的问题发送给外部日本养殖专家，获取专业建议，然后结合专家建议生成最终回答。

## 工作流程

```
用户输入: "那pH值呢？"
    ↓
查询重写智能体
    ↓
重写为: "查询当前养殖池的pH值数据"
    ↓
外部专家咨询服务
    ↓
发送给专家API: POST /consult
    ↓
获取专家建议
    ↓
结合专家建议生成最终回答
```

## 配置说明

### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 外部专家服务配置
EXPERT_API_BASE_URL=https://expert-api.example.com
EXPERT_API_KEY=your_api_key_here
EXPERT_API_TIMEOUT=30
ENABLE_EXPERT_CONSULTATION=true
```

### 配置项说明

- `EXPERT_API_BASE_URL`: 专家API的基础地址（必需）
- `EXPERT_API_KEY`: 专家API的认证密钥（可选）
- `EXPERT_API_TIMEOUT`: 请求超时时间，单位秒（默认30秒）
- `ENABLE_EXPERT_CONSULTATION`: 是否启用专家咨询（默认true）

## 专家API接口规范

### 请求格式

**端点**: `POST {EXPERT_API_BASE_URL}/consult`

**请求头**:
```
Content-Type: application/json
Authorization: Bearer {EXPERT_API_KEY}  # 如果配置了API密钥
```

**请求体**:
```json
{
  "query": "查询当前养殖池的pH值数据",
  "session_id": "session_123",
  "context": {
    "original_query": "那pH值呢？",
    "intent": "数据查询"
  },
  "timestamp": "2025-12-11T13:00:00"
}
```

### 响应格式

**成功响应** (200 OK):
```json
{
  "answer": "根据当前数据，1号池的pH值为7.2，处于正常范围（6.5-8.5）。建议继续保持当前水质管理措施。",
  "confidence": 0.95,
  "sources": [
    "日本陆上养殖水质标准手册",
    "pH值监测数据记录"
  ],
  "metadata": {
    "expert_id": "expert_001",
    "response_time": 1.2
  }
}
```

**错误响应** (4xx/5xx):
```json
{
  "error": "错误信息",
  "code": "ERROR_CODE"
}
```

## 使用示例

### 示例 1: 正常流程

**用户输入**: "那pH值呢？"

**查询重写**: "查询当前养殖池的pH值数据"

**专家咨询**:
- 请求: `POST /consult` with `{"query": "查询当前养殖池的pH值数据", ...}`
- 响应: `{"answer": "1号池的pH值为7.2...", "confidence": 0.95}`

**最终回答**: 结合专家建议和数据库查询结果生成

### 示例 2: 专家服务不可用

如果专家服务不可用（未配置、超时、错误等），系统会：
1. 记录警告日志
2. 继续使用数据库查询和AI分析
3. 不中断对话流程

## 控制台输出

每次专家咨询后，会在控制台打印：

```
================================================================================
👨‍🔬 专家咨询结果:
   专家回答: 根据当前数据，1号池的pH值为7.2，处于正常范围...
   置信度: 0.95
================================================================================
```

如果咨询失败：

```
================================================================================
⚠️  专家咨询失败:
   错误: HTTP错误: 500
================================================================================
```

## 技术实现

### 1. ExpertConsultationService 类

位置: `services/expert_consultation_service.py`

主要方法:
- `consult()`: 咨询外部专家
- `batch_consult()`: 批量咨询（未来扩展）

### 2. 集成点

在 `main.py` 的对话流程中：

```python
# 0.5. 查询重写
rewritten_query, rewrite_stats = await query_rewriter.rewrite(...)

# 0.6. 咨询外部专家
expert_response = await expert_service.consult(
    query=rewritten_query,
    context={...},
    session_id=session_id,
)

# 4. 生成回答（结合专家建议）
thinking_context = {
    ...
    "expert_advice": expert_response.get("answer", ""),
    "expert_confidence": expert_response.get("confidence", 0.0),
}
analysis = await thinking_agent.think(..., context=thinking_context)
```

### 3. 错误处理

- **超时**: 返回 `{"success": False, "error": "专家咨询超时"}`
- **HTTP错误**: 返回 `{"success": False, "error": "HTTP错误: {status_code}"}`
- **其他错误**: 返回 `{"success": False, "error": "{error_message}"}`

所有错误都不会中断对话流程，系统会继续使用其他数据源。

## 测试

### 1. 测试专家服务（未配置）

```python
from services.expert_consultation_service import expert_service

# 未配置API地址时
result = await expert_service.consult("测试问题")
# 返回: {"success": False, "error": "专家API地址未配置"}
```

### 2. 测试专家服务（已配置）

```python
# 配置API地址后
result = await expert_service.consult("查询pH值")
if result.get("success"):
    print(f"专家回答: {result['answer']}")
    print(f"置信度: {result['confidence']}")
else:
    print(f"错误: {result['error']}")
```

## 注意事项

1. **API地址配置**: 必须配置 `EXPERT_API_BASE_URL` 才能使用专家服务
2. **超时设置**: 默认30秒，可根据实际情况调整
3. **错误处理**: 专家服务失败不会影响对话流程
4. **性能考虑**: 专家咨询会增加一次HTTP请求，可能影响响应时间
5. **安全性**: 如果使用API密钥，请妥善保管，不要提交到代码仓库

## 未来扩展

- [ ] 支持多个专家源
- [ ] 专家建议缓存
- [ ] 专家建议评分和排序
- [ ] 异步专家咨询（不阻塞主流程）
- [ ] 专家建议的引用和溯源

