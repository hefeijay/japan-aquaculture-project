# API 文档说明

本目录包含日本陆上养殖生产管理AI助手服务端的API文档。

## 文件说明

- `openapi.yaml` - OpenAPI 3.0 格式的接口文档，可直接导入到 APIfox、Postman、Swagger UI 等工具

## 导入到 APIfox

APIfox 支持导入 OpenAPI 3.0 格式的文档。本目录提供了两种格式：
- `openapi.yaml` - YAML 格式（推荐）
- `openapi.json` - JSON 格式

### 方法一：直接导入文件（推荐）

1. 打开 APIfox 客户端或网页版
2. 进入项目，点击左侧菜单的 **"导入"** 按钮
3. 选择 **"OpenAPI"** 或 **"Swagger"**
4. 选择导入方式：
   - **从文件导入**：选择 `openapi.yaml` 或 `openapi.json` 文件
   - **从URL导入**：如果文档已部署，输入文档URL
5. 选择导入位置（新建项目或现有项目）
6. 点击 **"确认导入"**

### 方法二：拖拽导入

1. 打开 APIfox
2. 直接将 `openapi.yaml` 或 `openapi.json` 文件拖拽到 APIfox 界面
3. 按照提示完成导入

### 导入后验证

导入成功后，你应该能看到：
- **文件上传** 标签下的两个接口
  - `POST /api/upload` - 单文件上传
  - `POST /api/upload/multiple` - 多文件上传
- 每个接口都包含完整的请求参数、响应示例和错误处理说明

## 接口说明

### 文件上传接口

#### 1. 单文件上传
- **路径**: `POST /api/upload`
- **描述**: 接收单个文件并可选地转发到配置的地址
- **文件字段名**: `file`
- **支持的文件类型**: txt, pdf, png, jpg, jpeg, gif, zip, json, csv, xlsx, doc, docx

#### 2. 多文件上传
- **路径**: `POST /api/upload/multiple`
- **描述**: 接收多个文件并可选地转发到配置的地址
- **文件字段名**: `files[]`
- **支持的文件类型**: 同上

## 配置说明

### 文件转发配置

文件转发功能通过环境变量 `FILE_FORWARD_URL` 配置：

- **启用转发**: 设置 `FILE_FORWARD_URL=http://example.com/api/upload`
- **禁用转发**: 设置 `FILE_FORWARD_URL=none` 或不设置

配置文件位置：
- 环境变量
- `.env` 文件（项目根目录或 `japan_server/` 目录）

## 使用示例

### cURL 示例

#### 单文件上传
```bash
curl -X POST http://localhost:5002/api/upload \
  -F "file=@/path/to/file.txt" \
  -F "description=测试文件"
```

#### 多文件上传
```bash
curl -X POST http://localhost:5002/api/upload/multiple \
  -F "files[]=@/path/to/file1.txt" \
  -F "files[]=@/path/to/file2.pdf" \
  -F "description=批量上传"
```

### JavaScript 示例

#### 单文件上传
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('description', '测试文件');

fetch('http://localhost:5002/api/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

#### 多文件上传
```javascript
const formData = new FormData();
for (let file of fileInput.files) {
  formData.append('files[]', file);
}
formData.append('description', '批量上传');

fetch('http://localhost:5002/api/upload/multiple', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 响应格式

### 成功响应（单文件）
```json
{
  "success": true,
  "filename": "example.txt",
  "size": 1024,
  "timestamp": 1704067200000,
  "forward": {
    "enabled": true,
    "url": "http://example.com/api/upload",
    "success": true,
    "status_code": 200,
    "response": {
      "message": "File uploaded successfully"
    }
  }
}
```

### 成功响应（多文件）
```json
{
  "success": true,
  "files": [
    {
      "filename": "file1.txt",
      "size": 1024,
      "success": true,
      "forward": {
        "enabled": false,
        "url": null,
        "success": null,
        "error": null
      }
    }
  ],
  "count": 1,
  "timestamp": 1704067200000
}
```

### 错误响应
```json
{
  "success": false,
  "error": "未找到文件，请使用 'file' 作为文件字段名",
  "timestamp": 1704067200000
}
```

## 更新日志

- 2024-01-XX: 初始版本，包含单文件和多文件上传接口

