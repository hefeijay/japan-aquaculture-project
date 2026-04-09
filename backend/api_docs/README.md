# API 文档说明

本目录保存 `backend/` 的接口文档和导入说明。  
当前最常用的是文件上传接口的 OpenAPI 文档。

## 文件说明

- `openapi.yaml`：OpenAPI 3.0 文档，推荐用于 APIfox、Postman、Swagger UI 导入。

## 当前已确认的上传接口

- `POST /api/v1/upload`
- `POST /api/v1/upload/multiple`

注意：旧文档里出现过 `/api/upload`、`/api/upload/multiple`，当前代码实际蓝图前缀是 `/api/v1`，应以 `routes/file_upload_routes.py` 为准。

## 导入到 APIfox

1. 打开 APIfox。
2. 选择“导入”。
3. 选择 OpenAPI/Swagger。
4. 导入 `openapi.yaml`。

导入成功后应看到：

- `POST /api/v1/upload`
- `POST /api/v1/upload/multiple`

## 接口说明

### 单文件上传

- 路径：`POST /api/v1/upload`
- 文件字段名：`file`
- 描述：接收单个文件，并可按 `FILE_FORWARD_URL` 配置转发到外部服务

### 多文件上传

- 路径：`POST /api/v1/upload/multiple`
- 文件字段名：`files[]`
- 描述：接收多个文件，并可按 `FILE_FORWARD_URL` 配置转发

## 配置说明

### 文件转发

通过环境变量 `FILE_FORWARD_URL` 配置：

- 启用：`FILE_FORWARD_URL=http://example.com/api/upload`
- 禁用：不设置，或按当前部署约定关闭

配置来源建议优先看：

- 运行环境变量
- `backend/config/settings.py`
- 项目根 `.env` 或 `backend/.env`

不要再参考旧的 `japan_server/` 目录说明。

## 使用示例

### cURL

#### 单文件上传

```bash
curl -X POST http://localhost:5002/api/v1/upload \
  -F "file=@/path/to/file.txt" \
  -F "description=测试文件"
```

#### 多文件上传

```bash
curl -X POST http://localhost:5002/api/v1/upload/multiple \
  -F "files[]=@/path/to/file1.txt" \
  -F "files[]=@/path/to/file2.pdf" \
  -F "description=批量上传"
```

### JavaScript

#### 单文件上传

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("description", "测试文件");

fetch("http://localhost:5002/api/v1/upload", {
  method: "POST",
  body: formData,
})
  .then((response) => response.json())
  .then((data) => console.log(data));
```

#### 多文件上传

```javascript
const formData = new FormData();
for (const file of fileInput.files) {
  formData.append("files[]", file);
}
formData.append("description", "批量上传");

fetch("http://localhost:5002/api/v1/upload/multiple", {
  method: "POST",
  body: formData,
})
  .then((response) => response.json())
  .then((data) => console.log(data));
```

## 提醒

1. 默认端口是 `5002`，如果实际部署改过，请以生产反向代理和运行配置为准。
2. 上传接口的真实性能、文件大小限制和落盘策略，仍应结合当前代码和运行环境核对。

