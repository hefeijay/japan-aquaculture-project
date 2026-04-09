# APIfox 导入指南

本指南用于导入 `backend/api_docs/openapi.yaml`。

## 当前应看到的接口

导入成功后，上传接口应为：

- `POST /api/v1/upload`
- `POST /api/v1/upload/multiple`

如果你在 APIfox 中看到的是 `/api/upload` 或 `/api/upload/multiple`，说明导入的文档版本过旧，或参考了历史说明。

## 导入步骤

1. 打开 APIfox。
2. 选择“导入”。
3. 选择 OpenAPI/Swagger。
4. 选择 `openapi.yaml`。
5. 完成导入。

## 建议环境变量

```text
base_url = http://localhost:5002
forward_url = http://example.com/api/upload
```

## 测试单文件上传

1. 打开 `POST /api/v1/upload`。
2. 选择 `form-data`。
3. 添加字段：
   - `file`：文件
   - `description`：可选文本
4. 发送请求。

## 测试多文件上传

1. 打开 `POST /api/v1/upload/multiple`。
2. 选择 `form-data`。
3. 重复添加字段：
   - `files[]`：文件
4. 发送请求。

## 常见问题

### 导入后接口路径不对

- 以 `openapi.yaml` 和当前代码 `routes/file_upload_routes.py` 为准。
- 当前真实前缀是 `/api/v1`。

### 文件上传失败

- 确认服务运行在 `http://localhost:5002`
- 确认字段名正确：单文件用 `file`，多文件用 `files[]`
- 检查 `FILE_FORWARD_URL` 是否影响转发行为

## 提醒

1. 本目录的接口说明只覆盖当前 OpenAPI 文档涉及的能力，不代表整个 Backend 的全部接口。
2. 生产环境若有反向代理，请把 `base_url` 改成真实地址。




