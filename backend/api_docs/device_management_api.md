# 设备管理 API 文档

## 概述

设备管理API提供完整的设备管理功能，包括：
- 设备列表查询（支持筛选和搜索）
- 设备详情查看
- 设备信息编辑
- 设备删除
- 新设备登记

**Base URL**: `/api/v1`

---

## 接口列表

### 1. 获取设备列表

**接口地址**: `GET /devices`

**接口描述**: 获取所有设备列表，支持多条件筛选和搜索

#### 请求参数（Query Parameters）

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| status | string | 否 | 设备状态筛选<br>- `all`: 全部（默认）<br>- `online`: 在线<br>- `offline`: 离线 | `online` |
| pond_id | integer | 否 | 养殖池ID筛选 | `1` |
| control_mode | string | 否 | 权限分配筛选<br>- `manual_only`: 仅人工<br>- `ai_only`: 仅AI<br>- `hybrid`: 人工/AI | `hybrid` |
| search | string | 否 | 搜索关键词（支持设备名称或设备ID） | `传感器01` |
| page | integer | 否 | 页码（从1开始，默认为1） | `1` |
| page_size | integer | 否 | 每页数量（默认20，最大100） | `20` |

#### 响应示例

```json
{
  "code": 200,
  "message": "获取设备列表成功",
  "data": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3,
    "items": [
      {
        "id": 1,
        "device_id": "DEV-SENSOR-001",
        "name": "一号池溶解氧传感器",
        "status": "online",
        "control_mode": "hybrid",
        "control_mode_display": "人工/AI",
        "pond_id": 1,
        "pond_name": "一号养殖池",
        "device_type_id": 1,
        "device_type_name": "溶解氧传感器",
        "device_category": "sensor",
        "created_at": "2026-01-14T10:30:00Z",
        "updated_at": "2026-01-14T10:30:00Z"
      }
    ]
  }
}
```

#### 列表项字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 设备主键ID |
| device_id | string | 设备唯一标识符（业务ID） |
| name | string | 设备名称 |
| status | string | 设备状态（`online`=在线, `offline`=离线） |
| control_mode | string | 权限分配模式代码 |
| control_mode_display | string | 权限分配显示文本 |
| pond_id | integer/null | 养殖池ID |
| pond_name | string/null | 养殖池名称 |
| device_type_id | integer | 设备类型ID |
| device_type_name | string | 设备类型名称 |
| device_category | string | 设备大类（`sensor`/`feeder`/`camera`） |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

### 2. 获取设备详情

**接口地址**: `GET /devices/{id}`

**接口描述**: 获取指定设备的详细信息（包含基础字段和根据设备类型返回的扩展字段）

**重要说明**：响应数据采用嵌套结构，根据 `device_category` 的值返回对应的扩展字段：
- `device_category = "sensor"` → 返回 `sensor_fields`
- `device_category = "feeder"` → 返回 `feeder_fields`
- `device_category = "camera"` → 返回 `camera_fields`

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 设备ID |

---

#### 响应示例1：传感器设备详情

```json
{
  "code": 200,
  "message": "获取设备详情成功",
  "data": {
    "id": 1,
    "device_id": "DEV-SENSOR-001",
    "name": "一号池溶解氧传感器",
    "description": "用于监测一号池的溶解氧浓度",
    "ownership": "ABQ养殖场",
    "device_type_id": 1,
    "device_type_name": "溶解氧传感器",
    "device_category": "sensor",
    "model": "DO-2000",
    "manufacturer": "海洋仪器公司",
    "serial_number": "SN123456789",
    "location": "一号池中央区域",
    "pond_id": 1,
    "pond_name": "一号养殖池",
    "firmware_version": "v1.2.3",
    "hardware_version": "v2.0",
    "ip_address": "192.168.1.100",
    "mac_address": "00:1A:2B:3C:4D:5E",
    "config_json": {
      "sampling_rate": 60,
      "alert_threshold": 5.0
    },
    "tags": "重点监控,核心设备",
    "status": "online",
    "control_mode": "hybrid",
    "control_mode_display": "人工/AI",
    "created_at": "2026-01-14T10:30:00Z",
    "updated_at": "2026-01-14T10:30:00Z",
    "sensor_fields": {
      "id": 101,
      "sensor_type_id": 1,
      "sensor_type_name": "溶解氧传感器",
      "created_at": "2026-01-14T10:30:00Z",
      "updated_at": "2026-01-14T10:30:00Z"
    }
  }
}
```

#### 响应示例2：喂食机设备详情

```json
{
  "code": 200,
  "message": "获取设备详情成功",
  "data": {
    "id": 2,
    "device_id": "DEV-FEEDER-001",
    "name": "一号池自动喂食机",
    "description": "自动投喂系统",
    "ownership": "ABQ养殖场",
    "device_type_id": 5,
    "device_type_name": "自动喂食机",
    "device_category": "feeder",
    "model": "AF-3000",
    "manufacturer": "智能养殖设备公司",
    "serial_number": "SN987654321",
    "location": "一号池北侧",
    "pond_id": 1,
    "pond_name": "一号养殖池",
    "status": "online",
    "control_mode": "ai_only",
    "control_mode_display": "仅AI",
    "created_at": "2026-01-14T10:30:00Z",
    "updated_at": "2026-01-14T10:30:00Z",
    "feeder_fields": {
      "id": 201,
      "feed_count": 3,
      "feed_portion_weight": 20.0,
      "timezone": 9,
      "network_type": 0,
      "group_id": "GROUP-A",
      "capacity_kg": 100.0,
      "feed_type": "虾料A型",
      "created_at": "2026-01-14T10:30:00Z",
      "updated_at": "2026-01-14T10:30:00Z"
    }
  }
}
```

#### 响应示例3：摄像头设备详情

```json
{
  "code": 200,
  "message": "获取设备详情成功",
  "data": {
    "id": 3,
    "device_id": "DEV-CAMERA-001",
    "name": "一号池监控摄像头",
    "description": "高清监控摄像头",
    "ownership": "ABQ养殖场",
    "device_type_id": 10,
    "device_type_name": "监控摄像头",
    "device_category": "camera",
    "model": "CAM-4K-PRO",
    "ip_address": "192.168.1.200",
    "pond_id": 1,
    "pond_name": "一号养殖池",
    "status": "online",
    "control_mode": "manual_only",
    "control_mode_display": "仅人工",
    "created_at": "2026-01-14T10:30:00Z",
    "updated_at": "2026-01-14T10:30:00Z",
    "camera_fields": {
      "id": 301,
      "quality": "高",
      "connectivity": 100,
      "temperature": 25.5,
      "resolution": "1920x1080",
      "fps": 30,
      "codec": "H.264",
      "stream_url": "rtsp://192.168.1.200:554/stream",
      "recording": true,
      "night_vision": true,
      "motion_detection": true,
      "created_at": "2026-01-14T10:30:00Z",
      "updated_at": "2026-01-14T10:30:00Z"
    }
  }
}
```

---

#### 基础字段说明（所有设备类型）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 设备主键ID |
| device_id | string | 设备唯一标识符（业务ID） |
| name | string | 设备名称 |
| description | string/null | 设备描述 |
| ownership | string | 设备归属 |
| device_type_id | integer | 设备类型ID |
| device_type_name | string | 设备类型名称 |
| device_category | string | 设备大类（**用于判断有哪个扩展字段**） |
| model | string/null | 设备型号 |
| manufacturer | string/null | 制造商 |
| serial_number | string/null | 设备序列号 |
| location | string/null | 设备安装位置 |
| pond_id | integer/null | 所属养殖池ID |
| pond_name | string/null | 养殖池名称 |
| firmware_version | string/null | 固件版本 |
| hardware_version | string/null | 硬件版本 |
| ip_address | string/null | 设备IP地址 |
| mac_address | string/null | MAC地址 |
| config_json | object/null | 设备配置参数（JSON格式） |
| tags | string/null | 设备标签（逗号分隔） |
| status | string | 设备状态 |
| control_mode | string | 控制权限模式 |
| control_mode_display | string | 权限分配显示文本 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

#### 传感器扩展字段（sensor_fields）

**当 device_category = "sensor" 时返回**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 传感器扩展表ID |
| sensor_type_id | integer | 传感器类型ID |
| sensor_type_name | string | 传感器类型名称 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

#### 喂食机扩展字段（feeder_fields）

**当 device_category = "feeder" 时返回**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 喂食机扩展表ID |
| feed_count | integer | 默认喂食份数 |
| feed_portion_weight | decimal | 每份饲料重量（克） |
| timezone | integer | 时区（UTC+） |
| network_type | integer | 网络类型（0=WiFi, 1=4G） |
| group_id | string/null | 设备分组ID |
| capacity_kg | decimal/null | 饲料容量（千克） |
| feed_type | string/null | 饲料类型 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

#### 摄像头扩展字段（camera_fields）

**当 device_category = "camera" 时返回**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 摄像头扩展表ID |
| quality | string/null | 画质（高/中/低） |
| connectivity | integer | 连通性百分比 |
| temperature | decimal/null | 温度 |
| last_update | integer/null | 最后更新时间戳(毫秒) |
| last_update_time | string/null | 最后更新时间字符串 |
| resolution | string/null | 分辨率 |
| fps | integer | 帧率 |
| codec | string/null | 编解码 |
| stream_url | string/null | 流媒体地址 |
| recording | boolean | 是否正在录制 |
| night_vision | boolean | 是否开启夜视功能 |
| motion_detection | boolean | 是否开启运动检测 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

---

### 3. 登记新设备

**接口地址**: `POST /devices`

**接口描述**: 创建新设备记录

**重要说明**：创建设备时，需要根据设备类型（device_category）提供不同的扩展字段：
- **传感器(sensor)**: 必须提供 `sensor_fields`
- **喂食机(feeder)**: 可提供 `feeder_fields`
- **摄像头(camera)**: 可提供 `camera_fields`

#### 请求体结构

请求体分为两部分：
1. **基础字段**（devices表）- 所有设备类型都需要
2. **扩展字段**（sensors/feeders/cameras表）- 根据设备类型提供

---

#### 示例1：创建传感器设备

```json
{
  "device_id": "DEV-SENSOR-001",
  "name": "一号池溶解氧传感器",
  "device_type_id": 1,
  "pond_id": 1,
  "control_mode": "hybrid",
  "description": "用于监测一号池的溶解氧浓度",
  "ownership": "ABQ养殖场",
  "model": "DO-2000",
  "manufacturer": "海洋仪器公司",
  "serial_number": "SN123456789",
  "location": "一号池中央区域",
  "ip_address": "192.168.1.100",
  "mac_address": "00:1A:2B:3C:4D:5E",
  "tags": "重点监控,核心设备",
  "sensor_fields": {
    "sensor_type_id": 1
  }
}
```

#### 示例2：创建喂食机设备

```json
{
  "device_id": "DEV-FEEDER-001",
  "name": "一号池自动喂食机",
  "device_type_id": 5,
  "pond_id": 1,
  "control_mode": "hybrid",
  "description": "自动投喂系统",
  "ownership": "ABQ养殖场",
  "config_json": {
    "api_endpoint": "https://cloud.feeder.com/api",
    "api_key": "xxx"
  },
  "feeder_fields": {
    "feed_count": 3,
    "feed_portion_weight": 20.0,
    "timezone": 9,
    "network_type": 0,
    "group_id": "GROUP-A",
    "capacity_kg": 100.0,
    "feed_type": "虾料A型"
  }
}
```

#### 示例3：创建摄像头设备

```json
{
  "device_id": "DEV-CAMERA-001",
  "name": "一号池监控摄像头",
  "device_type_id": 10,
  "pond_id": 1,
  "control_mode": "manual_only",
  "description": "高清监控摄像头",
  "ownership": "ABQ养殖场",
  "ip_address": "192.168.1.200",
  "camera_fields": {
    "quality": "高",
    "connectivity": 100,
    "resolution": "1920x1080",
    "fps": 30,
    "codec": "H.264",
    "stream_url": "rtsp://192.168.1.200:554/stream",
    "recording": true,
    "night_vision": true,
    "motion_detection": true
  }
}
```

---

#### 基础字段说明（所有设备类型）

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| device_id | string | **是** | 设备唯一标识符（业务ID），1-128字符 |
| name | string | **是** | 设备名称，1-128字符 |
| device_type_id | integer | **是** | 设备类型ID（决定设备大类） |
| control_mode | string | **是** | 控制权限模式（`manual_only`/`ai_only`/`hybrid`） |
| pond_id | integer | 否 | 养殖池ID |
| config_json | object | 否 | 设备连接配置（JSON格式） |
| description | string | 否 | 设备描述 |
| ownership | string | 否 | 设备归属（默认："默认归属"） |
| model | string | 否 | 设备型号 |
| manufacturer | string | 否 | 制造商 |
| serial_number | string | 否 | 设备序列号 |
| location | string | 否 | 设备安装位置 |
| ip_address | string | 否 | 设备IP地址 |
| mac_address | string | 否 | MAC地址 |
| tags | string | 否 | 设备标签（逗号分隔） |

---

#### 传感器扩展字段（sensor_fields）

**当设备类型为传感器时必填**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| sensor_type_id | integer | **是** | 传感器类型ID（FK → sensor_types.id） |

---

#### 喂食机扩展字段（feeder_fields）

**当设备类型为喂食机时使用**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| feed_count | integer | 否 | 1 | 默认喂食份数 |
| feed_portion_weight | decimal | 否 | 17.0 | 每份饲料重量（克） |
| timezone | integer | 否 | 9 | 时区（UTC+） |
| network_type | integer | 否 | 0 | 网络类型（0=WiFi, 1=4G） |
| group_id | string | 否 | - | 设备分组ID |
| capacity_kg | decimal | 否 | - | 饲料容量（千克） |
| feed_type | string | 否 | - | 饲料类型 |

---

#### 摄像头扩展字段（camera_fields）

**当设备类型为摄像头时使用**

| 字段名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| quality | string | 否 | - | 画质（高/中/低） |
| connectivity | integer | 否 | 0 | 连通性百分比 |
| temperature | decimal | 否 | - | 温度 |
| resolution | string | 否 | - | 分辨率（如：1920x1080） |
| fps | integer | 否 | 0 | 帧率 |
| codec | string | 否 | - | 编解码（如：H.264） |
| stream_url | string | 否 | - | 流媒体地址 |
| recording | boolean | 否 | false | 是否正在录制 |
| night_vision | boolean | 否 | false | 是否开启夜视功能 |
| motion_detection | boolean | 否 | false | 是否开启运动检测 |

#### 响应示例

```json
{
  "code": 201,
  "message": "设备登记成功",
  "data": {
    "id": 1,
    "device_id": "DEV-SENSOR-001",
    "name": "一号池溶解氧传感器",
    ...
  }
}
```

#### 错误响应

**设备ID已存在** (409)
```json
{
  "code": 409,
  "message": "设备ID已存在"
}
```

---

### 4. 编辑设备

**接口地址**: `PUT /devices/{id}`

**接口描述**: 更新设备信息（支持修改设备名称、类型、权限、养殖池位、描述等）

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 设备ID |

#### 请求体（Request Body）

```json
{
  "name": "一号池溶解氧传感器（升级版）",
  "device_type_id": 2,
  "pond_id": 2,
  "control_mode": "manual_only",
  "description": "更新后的设备描述",
  "ownership": "ABQ养殖场",
  "model": "DO-2000 Pro",
  "location": "二号池东侧区域",
  "firmware_version": "v1.3.0",
  "hardware_version": "v2.1",
  "ip_address": "192.168.1.101",
  "mac_address": "00:1A:2B:3C:4D:5F",
  "config_json": {
    "sampling_rate": 30,
    "alert_threshold": 6.0
  },
  "tags": "重点监控,已升级",
  "status": "online"
}
```

#### 请求字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 设备名称 |
| device_type_id | integer | 否 | 设备类型ID |
| pond_id | integer/null | 否 | 养殖池ID（可移动设备到不同池位） |
| control_mode | string | 否 | 控制权限模式 |
| description | string/null | 否 | 设备描述 |
| ownership | string | 否 | 设备归属 |
| model | string/null | 否 | 设备型号 |
| manufacturer | string/null | 否 | 制造商 |
| serial_number | string/null | 否 | 设备序列号 |
| location | string/null | 否 | 设备安装位置 |
| firmware_version | string/null | 否 | 固件版本 |
| hardware_version | string/null | 否 | 硬件版本 |
| ip_address | string/null | 否 | 设备IP地址 |
| mac_address | string/null | 否 | MAC地址 |
| config_json | object/null | 否 | 设备配置参数 |
| tags | string/null | 否 | 设备标签 |
| status | string | 否 | 设备状态（`online`/`offline`） |

**注意**: 所有字段都是可选的，只需传入需要更新的字段即可。

#### 响应示例

```json
{
  "code": 200,
  "message": "设备更新成功",
  "data": {
    "id": 1,
    "device_id": "DEV-SENSOR-001",
    "name": "一号池溶解氧传感器（升级版）",
    ...
  }
}
```

---

### 5. 删除设备

**接口地址**: `DELETE /devices/{id}`

**接口描述**: 物理删除指定设备（不可恢复）

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | integer | 是 | 设备ID |

#### 响应示例

```json
{
  "code": 200,
  "message": "设备删除成功"
}
```

---

## 通用错误响应

### 400 Bad Request - 请求参数错误

```json
{
  "code": 400,
  "message": "请求参数错误",
  "errors": {
    "name": "设备名称不能为空",
    "device_type_id": "设备类型ID必须是有效的整数"
  }
}
```

### 404 Not Found - 资源不存在

```json
{
  "code": 404,
  "message": "设备不存在"
}
```

### 500 Internal Server Error - 服务器内部错误

```json
{
  "code": 500,
  "message": "服务器内部错误"
}
```

---

## 数据字典

### 设备状态 (status)

| 值 | 说明 |
|----|------|
| online | 在线 |
| offline | 离线 |

### 权限分配模式 (control_mode)

| 值 | 显示文本 | 说明 |
|----|---------|------|
| manual_only | 仅人工 | 只允许人工控制 |
| ai_only | 仅AI | 只允许AI控制 |
| hybrid | 人工/AI | 允许人工和AI协同控制 |

### 设备大类 (device_category)

| 值 | 说明 |
|----|------|
| sensor | 传感器 |
| feeder | 喂食机 |
| camera | 摄像头 |

---

## 前端集成示例

### 示例1: 获取设备列表（带筛选）

```javascript
// 获取在线状态的传感器设备
const response = await fetch('/api/v1/devices?status=online&pond_id=1&page=1&page_size=20', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
});

const result = await response.json();
console.log(result.data.items); // 设备列表
```

### 示例2: 搜索设备

```javascript
// 按设备名称或ID搜索
const response = await fetch('/api/v1/devices?search=传感器', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
});

const result = await response.json();
```

### 示例2.5: 获取设备详情并根据类型展示

```javascript
// 获取设备详情
const response = await fetch('/api/v1/devices/1', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  }
});

const result = await response.json();
const device = result.data;

// 根据设备类型渲染不同的扩展信息
function renderDeviceDetail(device) {
  // 渲染基础信息（所有设备通用）
  console.log(`设备名称: ${device.name}`);
  console.log(`设备ID: ${device.device_id}`);
  console.log(`设备状态: ${device.status}`);
  console.log(`养殖池: ${device.pond_name}`);
  
  // 根据device_category渲染扩展信息
  switch(device.device_category) {
    case 'sensor':
      if (device.sensor_fields) {
        console.log('=== 传感器信息 ===');
        console.log(`传感器类型: ${device.sensor_fields.sensor_type_name}`);
      }
      break;
      
    case 'feeder':
      if (device.feeder_fields) {
        console.log('=== 喂食机信息 ===');
        console.log(`喂食份数: ${device.feeder_fields.feed_count}`);
        console.log(`每份重量: ${device.feeder_fields.feed_portion_weight}克`);
        console.log(`饲料容量: ${device.feeder_fields.capacity_kg}kg`);
        console.log(`饲料类型: ${device.feeder_fields.feed_type}`);
      }
      break;
      
    case 'camera':
      if (device.camera_fields) {
        console.log('=== 摄像头信息 ===');
        console.log(`分辨率: ${device.camera_fields.resolution}`);
        console.log(`帧率: ${device.camera_fields.fps} FPS`);
        console.log(`流地址: ${device.camera_fields.stream_url}`);
        console.log(`夜视: ${device.camera_fields.night_vision ? '已开启' : '已关闭'}`);
      }
      break;
  }
}

renderDeviceDetail(device);
```

### 示例3: 登记新设备

#### 3.1 创建传感器设备

```javascript
const newSensor = {
  device_id: 'DEV-SENSOR-002',
  name: '二号池温度传感器',
  device_type_id: 2,
  pond_id: 2,
  control_mode: 'hybrid',
  description: '用于监测二号池温度',
  config_json: {
    sampling_rate: 30
  },
  // 传感器特有字段
  sensor_fields: {
    sensor_type_id: 2  // 必填
  }
};

const response = await fetch('/api/v1/devices', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(newSensor)
});

const result = await response.json();
```

#### 3.2 创建喂食机设备

```javascript
const newFeeder = {
  device_id: 'DEV-FEEDER-002',
  name: '二号池自动喂食机',
  device_type_id: 5,
  pond_id: 2,
  control_mode: 'ai_only',
  description: 'AI控制投喂系统',
  // 喂食机特有字段
  feeder_fields: {
    feed_count: 5,
    feed_portion_weight: 25.0,
    timezone: 9,
    network_type: 0,
    capacity_kg: 150.0,
    feed_type: '虾料B型'
  }
};

const response = await fetch('/api/v1/devices', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(newFeeder)
});

const result = await response.json();
```

#### 3.3 创建摄像头设备

```javascript
const newCamera = {
  device_id: 'DEV-CAMERA-002',
  name: '二号池监控摄像头',
  device_type_id: 10,
  pond_id: 2,
  control_mode: 'manual_only',
  description: '4K高清监控',
  ip_address: '192.168.1.201',
  // 摄像头特有字段
  camera_fields: {
    quality: '高',
    resolution: '3840x2160',
    fps: 60,
    codec: 'H.265',
    stream_url: 'rtsp://192.168.1.201:554/stream',
    recording: true,
    night_vision: true,
    motion_detection: false
  }
};

const response = await fetch('/api/v1/devices', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(newCamera)
});

const result = await response.json();
```

### 示例4: 编辑设备

```javascript
const updateData = {
  name: '二号池温度传感器（已升级）',
  pond_id: 3, // 移动到3号池
  control_mode: 'manual_only'
};

const response = await fetch('/api/v1/devices/1', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(updateData)
});

const result = await response.json();
```

### 示例5: 删除设备

```javascript
const response = await fetch('/api/v1/devices/1', {
  method: 'DELETE',
  headers: {
    'Content-Type': 'application/json'
  }
});

const result = await response.json();
```

---

## 前端实现指南

### 动态表单设计

创建设备时，前端应根据用户选择的设备类型动态显示不同的表单字段：

```javascript
// 1. 首先获取设备类型列表（需要额外的API）
// GET /api/v1/device-types

// 2. 用户选择设备类型后，根据device_category显示对应的扩展字段
const deviceTypeMap = {
  'sensor': {
    label: '传感器',
    requiredFields: ['sensor_type_id'],
    fields: [
      { name: 'sensor_type_id', label: '传感器类型', type: 'select', required: true }
    ]
  },
  'feeder': {
    label: '喂食机',
    requiredFields: [],
    fields: [
      { name: 'feed_count', label: '默认喂食份数', type: 'number', default: 1 },
      { name: 'feed_portion_weight', label: '每份饲料重量(克)', type: 'number', default: 17.0 },
      { name: 'timezone', label: '时区(UTC+)', type: 'number', default: 9 },
      { name: 'network_type', label: '网络类型', type: 'select', options: [{value: 0, label: 'WiFi'}, {value: 1, label: '4G'}] },
      { name: 'group_id', label: '设备分组ID', type: 'text' },
      { name: 'capacity_kg', label: '饲料容量(kg)', type: 'number' },
      { name: 'feed_type', label: '饲料类型', type: 'text' }
    ]
  },
  'camera': {
    label: '摄像头',
    requiredFields: [],
    fields: [
      { name: 'quality', label: '画质', type: 'select', options: ['高', '中', '低'] },
      { name: 'resolution', label: '分辨率', type: 'text', placeholder: '1920x1080' },
      { name: 'fps', label: '帧率', type: 'number', default: 0 },
      { name: 'codec', label: '编解码', type: 'text', placeholder: 'H.264' },
      { name: 'stream_url', label: '流媒体地址', type: 'text', placeholder: 'rtsp://...' },
      { name: 'recording', label: '是否录制', type: 'checkbox', default: false },
      { name: 'night_vision', label: '夜视功能', type: 'checkbox', default: false },
      { name: 'motion_detection', label: '运动检测', type: 'checkbox', default: false }
    ]
  }
};

// 3. 根据选择的设备类型，动态渲染表单
function renderDeviceForm(deviceCategory) {
  const config = deviceTypeMap[deviceCategory];
  if (!config) return null;
  
  return (
    <div>
      <h3>{config.label}特有配置</h3>
      {config.fields.map(field => (
        <FormField 
          key={field.name}
          {...field}
          required={config.requiredFields.includes(field.name)}
        />
      ))}
    </div>
  );
}

// 4. 提交时构建正确的请求体
function buildDevicePayload(basicFields, deviceCategory, extensionFields) {
  const payload = { ...basicFields };
  
  if (deviceCategory === 'sensor' && extensionFields) {
    payload.sensor_fields = extensionFields;
  } else if (deviceCategory === 'feeder' && extensionFields) {
    payload.feeder_fields = extensionFields;
  } else if (deviceCategory === 'camera' && extensionFields) {
    payload.camera_fields = extensionFields;
  }
  
  return payload;
}
```

### 设备详情的TypeScript类型定义

```typescript
// 设备详情完整类型定义
interface DeviceDetail {
  // 基础字段（所有设备通用）
  id: number;
  device_id: string;
  name: string;
  description: string | null;
  ownership: string;
  device_type_id: number;
  device_type_name: string;
  device_category: 'sensor' | 'feeder' | 'camera';  // 关键字段
  model: string | null;
  manufacturer: string | null;
  serial_number: string | null;
  location: string | null;
  pond_id: number | null;
  pond_name: string | null;
  firmware_version: string | null;
  hardware_version: string | null;
  ip_address: string | null;
  mac_address: string | null;
  config_json: Record<string, any> | null;
  tags: string | null;
  status: 'online' | 'offline';
  control_mode: 'manual_only' | 'ai_only' | 'hybrid';
  control_mode_display: string;
  created_at: string;
  updated_at: string;
  
  // 扩展字段（根据device_category，只会有其中一个）
  sensor_fields?: {
    id: number;
    sensor_type_id: number;
    sensor_type_name: string;
    created_at: string;
    updated_at: string;
  };
  
  feeder_fields?: {
    id: number;
    feed_count: number;
    feed_portion_weight: number;
    timezone: number;
    network_type: number;
    group_id: string | null;
    capacity_kg: number | null;
    feed_type: string | null;
    created_at: string;
    updated_at: string;
  };
  
  camera_fields?: {
    id: number;
    quality: string | null;
    connectivity: number;
    temperature: number | null;
    last_update: number | null;
    last_update_time: string | null;
    resolution: string | null;
    fps: number;
    codec: string | null;
    stream_url: string | null;
    recording: boolean;
    night_vision: boolean;
    motion_detection: boolean;
    created_at: string;
    updated_at: string;
  };
}

// React组件示例：设备详情展示
function DeviceDetailModal({ deviceId }: { deviceId: number }) {
  const [device, setDevice] = useState<DeviceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    async function fetchDetail() {
      try {
        const response = await fetch(`/api/v1/devices/${deviceId}`);
        const result = await response.json();
        if (result.code === 200) {
          setDevice(result.data);
        }
      } catch (error) {
        console.error('获取设备详情失败', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchDetail();
  }, [deviceId]);
  
  if (loading) return <div>加载中...</div>;
  if (!device) return <div>设备不存在</div>;
  
  return (
    <div className="device-detail">
      {/* 基础信息 - 所有设备类型通用 */}
      <section className="basic-info">
        <h2>基础信息</h2>
        <div className="info-grid">
          <div>设备名称：{device.name}</div>
          <div>设备ID：{device.device_id}</div>
          <div>状态：<span className={device.status}>{device.status === 'online' ? '在线' : '离线'}</span></div>
          <div>权限：{device.control_mode_display}</div>
          <div>养殖池：{device.pond_name || '未分配'}</div>
          <div>设备类型：{device.device_type_name}</div>
          <div>型号：{device.model || '-'}</div>
          <div>制造商：{device.manufacturer || '-'}</div>
        </div>
      </section>
      
      {/* 扩展信息 - 根据设备类型动态渲染 */}
      {device.device_category === 'sensor' && device.sensor_fields && (
        <section className="extension-info">
          <h2>传感器信息</h2>
          <div className="info-grid">
            <div>传感器类型：{device.sensor_fields.sensor_type_name}</div>
          </div>
        </section>
      )}
      
      {device.device_category === 'feeder' && device.feeder_fields && (
        <section className="extension-info">
          <h2>喂食机信息</h2>
          <div className="info-grid">
            <div>喂食份数：{device.feeder_fields.feed_count}</div>
            <div>每份重量：{device.feeder_fields.feed_portion_weight} 克</div>
            <div>饲料容量：{device.feeder_fields.capacity_kg || '-'} kg</div>
            <div>饲料类型：{device.feeder_fields.feed_type || '-'}</div>
            <div>时区：UTC+{device.feeder_fields.timezone}</div>
            <div>网络类型：{device.feeder_fields.network_type === 0 ? 'WiFi' : '4G'}</div>
          </div>
        </section>
      )}
      
      {device.device_category === 'camera' && device.camera_fields && (
        <section className="extension-info">
          <h2>摄像头信息</h2>
          <div className="info-grid">
            <div>分辨率：{device.camera_fields.resolution || '-'}</div>
            <div>帧率：{device.camera_fields.fps} FPS</div>
            <div>编解码：{device.camera_fields.codec || '-'}</div>
            <div>画质：{device.camera_fields.quality || '-'}</div>
            <div>连通性：{device.camera_fields.connectivity}%</div>
            <div>温度：{device.camera_fields.temperature || '-'} °C</div>
            <div>夜视功能：{device.camera_fields.night_vision ? '✅ 已开启' : '❌ 已关闭'}</div>
            <div>运动检测：{device.camera_fields.motion_detection ? '✅ 已开启' : '❌ 已关闭'}</div>
            <div>录制状态：{device.camera_fields.recording ? '🔴 录制中' : '⚫ 未录制'}</div>
          </div>
          {device.camera_fields.stream_url && (
            <div className="stream-info">
              <div>流媒体地址：</div>
              <code>{device.camera_fields.stream_url}</code>
              <button onClick={() => window.open(device.camera_fields.stream_url)}>
                播放视频流
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
```

---

### 获取设备类型的API

前端需要一个额外的API来获取设备类型列表及其category信息：

```javascript
// GET /api/v1/device-types
// 返回示例：
[
  {
    "id": 1,
    "category": "sensor",
    "name": "溶解氧传感器",
    "description": "用于监测水体溶解氧浓度"
  },
  {
    "id": 2,
    "category": "sensor",
    "name": "温度传感器",
    "description": "用于监测水温"
  },
  {
    "id": 5,
    "category": "feeder",
    "name": "自动喂食机",
    "description": "智能投喂设备"
  },
  {
    "id": 10,
    "category": "camera",
    "name": "监控摄像头",
    "description": "高清视频监控设备"
  }
]
```

---

## 注意事项

1. **设备ID唯一性**: `device_id` 必须在系统中唯一，重复注册会返回409错误
2. **物理删除**: 删除操作是物理删除，数据无法恢复，请谨慎操作
3. **设备移动**: 通过更新 `pond_id` 可以将设备移动到不同的养殖池
4. **分页查询**: 建议使用分页查询避免一次性加载过多数据
5. **搜索功能**: search参数支持模糊匹配设备名称和device_id
6. **筛选组合**: 可以同时使用多个筛选条件进行组合查询
7. **config_json格式**: 设备配置参数必须是有效的JSON对象
8. **扩展字段必填**: 创建传感器时，`sensor_fields.sensor_type_id` 是必填的
9. **动态表单**: 前端需要根据设备类型动态显示不同的表单字段
10. **两表联动**: 创建设备时会在devices表和对应的扩展表（sensors/feeders/cameras）中同时插入数据
11. **嵌套结构**: 设备详情采用嵌套结构，扩展字段根据 `device_category` 返回对应的 `sensor_fields` / `feeder_fields` / `camera_fields`
12. **数据一致性**: 创建和查询的数据结构保持一致，都使用嵌套结构，方便前端复用组件和类型定义
13. **扩展字段互斥**: 一个设备只会有一个扩展字段对象（sensor_fields/feeder_fields/camera_fields），不会同时存在多个

---

## 💡 API设计说明

### 嵌套结构返回模式

本API对于设备详情采用**嵌套结构**返回，即根据设备类型（device_category）动态返回对应的扩展字段：

| 设备类型 | 返回的扩展字段 | 示例 |
|---------|---------------|------|
| sensor  | `sensor_fields` | `{ sensor_type_id: 1, ... }` |
| feeder  | `feeder_fields` | `{ feed_count: 3, ... }` |
| camera  | `camera_fields` | `{ resolution: "1920x1080", ... }` |

**核心原则**：一个设备只返回一个扩展字段对象，不会同时存在多个扩展字段。

---

## 🎯 为什么使用嵌套结构？

### 方案对比

本API采用**嵌套结构**（方案2）而非扁平化结构（方案1），主要优势：

#### ✅ 优势1：数据结构清晰

```json
// ✅ 嵌套结构（采用）
{
  "device_id": "DEV-SENSOR-001",
  "name": "传感器",
  "device_category": "sensor",
  "sensor_fields": {
    "sensor_type_id": 1
  }
}

// ❌ 扁平结构（未采用）
{
  "device_id": "DEV-SENSOR-001",
  "name": "传感器",
  "sensor_type_id": 1,           // 传感器字段
  "feed_count": null,             // 喂食机字段（冗余null）
  "feed_portion_weight": null,    // 喂食机字段（冗余null）
  "resolution": null,             // 摄像头字段（冗余null）
  "fps": null                     // 摄像头字段（冗余null）
}
```

#### ✅ 优势2：与创建接口保持一致

创建和查询使用相同的数据结构，前端可以复用组件：

```typescript
// 创建设备
POST /devices
{
  "device_id": "xxx",
  "sensor_fields": { ... }
}

// 查询详情 - 结构一致！
GET /devices/1
{
  "device_id": "xxx",
  "sensor_fields": { ... }
}

// 前端可以复用同一个表单组件和类型定义
```

#### ✅ 优势3：易于扩展

新增设备类型时不会污染现有数据结构：

```json
// 未来新增"水泵"类型，只需添加新的扩展字段
{
  "device_category": "pump",
  "pump_fields": {
    "flow_rate": 100,
    "pressure": 5.0
  }
}
// 不影响现有的sensor/feeder/camera
```

#### ✅ 优势4：TypeScript友好

```typescript
// 类型推断清晰
if (device.device_category === 'sensor') {
  // TypeScript知道这里device.sensor_fields一定存在
  console.log(device.sensor_fields.sensor_type_id);
}
```

---

## 数据库设计说明

### 多表继承设计

本系统采用多表继承（Table Inheritance）设计模式：

```
┌─────────────────┐
│    devices      │  ← 基础表：存储所有设备的通用信息
│  (基础信息表)    │
└────────┬────────┘
         │ device_id (1对1)
         ├─────────────────────────────────┐
         │                                 │
         ▼                                 ▼
┌─────────────────┐              ┌─────────────────┐
│    sensors      │              │    feeders      │
│ (传感器扩展表)   │              │ (喂食机扩展表)   │
│ + sensor_type_id│              │ + feed_count    │
└─────────────────┘              │ + feed_portion  │
                                 │ + timezone      │
         ▼                       └─────────────────┘
┌─────────────────┐
│    cameras      │
│ (摄像头扩展表)   │
│ + resolution    │
│ + fps           │
│ + stream_url    │
└─────────────────┘
```

### 表关系说明

1. **devices表** (基础表)
   - 主键：`id`
   - 存储：设备通用信息（名称、状态、权限、位置等）

2. **sensors表** (扩展表)
   - 外键：`device_id` → `devices.id` (UNIQUE, 1对1)
   - 存储：传感器特有信息

3. **feeders表** (扩展表)
   - 外键：`device_id` → `devices.id` (UNIQUE, 1对1)
   - 存储：喂食机特有信息

4. **cameras表** (扩展表)
   - 外键：`device_id` → `devices.id` (UNIQUE, 1对1)
   - 存储：摄像头特有信息

### 创建设备的后端处理流程

```python
# 伪代码示例
def create_device(data):
    # 1. 先在devices表创建基础记录
    device = Device(
        device_id=data['device_id'],
        name=data['name'],
        device_type_id=data['device_type_id'],
        pond_id=data.get('pond_id'),
        control_mode=data['control_mode'],
        # ... 其他基础字段
    )
    db.add(device)
    db.flush()  # 获取device.id
    
    # 2. 根据device_type的category，在对应扩展表创建记录
    device_type = get_device_type(data['device_type_id'])
    
    if device_type.category == 'sensor':
        sensor = Sensor(
            device_id=device.id,
            name=device.name,  # 冗余字段
            pond_id=device.pond_id,  # 冗余字段
            sensor_type_id=data['sensor_fields']['sensor_type_id']
        )
        db.add(sensor)
    
    elif device_type.category == 'feeder':
        feeder = Feeder(
            device_id=device.id,
            name=device.name,
            pond_id=device.pond_id,
            feed_count=data['feeder_fields'].get('feed_count', 1),
            feed_portion_weight=data['feeder_fields'].get('feed_portion_weight', 17.0),
            # ... 其他喂食机字段
        )
        db.add(feeder)
    
    elif device_type.category == 'camera':
        camera = Camera(
            device_id=device.id,
            name=device.name,
            pond_id=device.pond_id,
            resolution=data['camera_fields'].get('resolution'),
            fps=data['camera_fields'].get('fps', 0),
            # ... 其他摄像头字段
        )
        db.add(camera)
    
    db.commit()
    return device
```

### 为什么要冗余name和pond_id？

在sensors/feeders/cameras表中，`name`和`pond_id`是从devices表同步的快照字段：

**优点**：
- 提高查询性能（无需JOIN）
- 保证历史数据一致性
- 优化LLM查询场景

**注意事项**：
- 更新devices表时，需要同步更新扩展表的冗余字段
- 以devices表为准（Single Source of Truth）

---

## 配置和字典接口

为了支持前端动态表单和筛选功能，提供以下配置和字典接口：

---

### 6. 获取养殖池列表

**接口地址**: `GET /ponds`

**接口描述**: 获取所有养殖池列表，用于设备创建/编辑时选择所属养殖池，以及列表筛选

#### 请求参数

无

#### 响应示例

```json
{
  "code": 200,
  "message": "获取养殖池列表成功",
  "data": [
    {
      "id": 1,
      "pond_id": "POND_001",
      "name": "1号养殖池",
      "location": "A区",
      "area": 100.0,
      "count": 50000,
      "description": "主养殖池"
    },
    {
      "id": 2,
      "pond_id": "POND_002",
      "name": "2号养殖池",
      "location": "B区",
      "area": 80.0,
      "count": 40000,
      "description": "备用养殖池"
    }
  ]
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 养殖池数据库主键ID |
| pond_id | string | 养殖池业务ID |
| name | string | 养殖池名称 |
| location | string/null | 位置信息 |
| area | float/null | 养殖池面积（平方米） |
| count | integer/null | 养殖数量（尾数） |
| description | string/null | 描述信息 |

---

### 7. 获取设备状态选项

**接口地址**: `GET /enums/device-status`

**接口描述**: 获取设备状态枚举列表，用于设备筛选和状态设置

#### 请求参数

无

#### 响应示例

```json
{
  "code": 200,
  "message": "获取设备状态选项成功",
  "data": [
    {
      "value": "online",
      "label": "在线",
      "description": "设备正常在线工作",
      "color": "#67C23A"
    },
    {
      "value": "offline",
      "label": "离线",
      "description": "设备已离线",
      "color": "#909399"
    },
    {
      "value": "active",
      "label": "活跃",
      "description": "设备正在活跃工作",
      "color": "#409EFF"
    },
    {
      "value": "inactive",
      "label": "不活跃",
      "description": "设备空闲状态",
      "color": "#E6A23C"
    }
  ]
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| value | string | 状态值（用于API传参） |
| label | string | 状态显示文本（用于前端展示） |
| description | string | 状态描述 |
| color | string | 建议的显示颜色（十六进制） |

---

### 8. 获取控制模式选项

**接口地址**: `GET /enums/control-modes`

**接口描述**: 获取设备控制模式枚举列表，用于权限分配设置

#### 请求参数

无

#### 响应示例

```json
{
  "code": 200,
  "message": "获取控制模式选项成功",
  "data": [
    {
      "value": "manual_only",
      "label": "仅人工",
      "description": "只允许人工手动控制",
      "icon": "user"
    },
    {
      "value": "ai_only",
      "label": "仅AI",
      "description": "只允许AI系统自动控制",
      "icon": "cpu"
    },
    {
      "value": "hybrid",
      "label": "混合模式",
      "description": "支持人工和AI协同控制",
      "icon": "share"
    }
  ]
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| value | string | 控制模式值（用于API传参） |
| label | string | 模式显示文本（用于前端展示） |
| description | string | 模式描述 |
| icon | string | 建议的图标名称 |

---

### 9. 获取设备类型列表

**接口地址**: `GET /device-types`

**接口描述**: 获取所有设备类型列表，用于设备创建时选择设备类型

#### 请求参数（Query Parameters）

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| category | string | 否 | 按设备大类筛选<br>- `sensor`: 传感器<br>- `feeder`: 喂食机<br>- `camera`: 摄像头 | `sensor` |

#### 响应示例

```json
{
  "code": 200,
  "message": "获取设备类型列表成功",
  "data": [
    {
      "id": 1,
      "category": "sensor",
      "name": "溶解氧传感器",
      "description": "用于监测水体溶解氧浓度"
    },
    {
      "id": 2,
      "category": "sensor",
      "name": "温度传感器",
      "description": "用于监测水温"
    },
    {
      "id": 5,
      "category": "feeder",
      "name": "自动喂食机",
      "description": "智能投喂设备"
    },
    {
      "id": 10,
      "category": "camera",
      "name": "监控摄像头",
      "description": "高清视频监控设备"
    }
  ]
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 设备类型ID |
| category | string | 设备大类（`sensor`/`feeder`/`camera`） |
| name | string | 设备类型名称（唯一标识） |
| description | string/null | 设备类型描述 |

#### 使用示例

```bash
# 获取所有设备类型
GET /api/v1/device-types

# 只获取传感器类型
GET /api/v1/device-types?category=sensor
```

---

### 10. 获取传感器类型列表

**接口地址**: `GET /sensor-types`

**接口描述**: 获取所有传感器类型列表，用于传感器设备创建时选择具体的传感器类型

**适用场景**: 仅当 `device_category = "sensor"` 时需要调用此接口

#### 请求参数

无

#### 响应示例

```json
{
  "code": 200,
  "message": "获取传感器类型列表成功",
  "data": [
    {
      "id": 1,
      "type_name": "溶解氧饱和度传感器",
      "metric": "do",
      "unit": "mg/L",
      "valid_min": 3.0,
      "valid_max": 15.0,
      "description": "测量水体溶解氧含量"
    },
    {
      "id": 2,
      "type_name": "液位传感器",
      "metric": "water_level",
      "unit": "mm",
      "valid_min": 500.0,
      "valid_max": 5000.0,
      "description": "测量水位高度"
    },
    {
      "id": 3,
      "type_name": "pH传感器",
      "metric": "ph",
      "unit": "pH",
      "valid_min": 6.0,
      "valid_max": 9.0,
      "description": "测量水体酸碱度"
    },
    {
      "id": 4,
      "type_name": "水温传感器",
      "metric": "temperature",
      "unit": "°C",
      "valid_min": 15.0,
      "valid_max": 35.0,
      "description": "测量水体温度"
    },
    {
      "id": 5,
      "type_name": "浊度传感器",
      "metric": "turbidity",
      "unit": "NTU",
      "valid_min": 0.0,
      "valid_max": 100.0,
      "description": "测量水体浊度"
    },
    {
      "id": 6,
      "type_name": "氨氮传感器",
      "metric": "ammonia",
      "unit": "mg/L",
      "valid_min": 0.0,
      "valid_max": 2.0,
      "description": "测量水体氨氮浓度"
    },
    {
      "id": 7,
      "type_name": "亚硝酸盐传感器",
      "metric": "nitrite",
      "unit": "mg/L",
      "valid_min": 0.0,
      "valid_max": 0.5,
      "description": "测量水体亚硝酸盐浓度"
    }
  ]
}
```

#### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 传感器类型ID |
| type_name | string | 传感器类型名称 |
| metric | string | 测量指标标识符（如：do, ph, temperature等） |
| unit | string | 数据单位（如：mg/L, °C, pH等） |
| valid_min | float/null | 有效值下限（用于异常检测） |
| valid_max | float/null | 有效值上限（用于异常检测） |
| description | string/null | 传感器类型描述 |

---

## 前端使用示例

### 设备创建表单数据加载

```javascript
// 页面加载时，获取所有必要的配置数据
async function initDeviceForm() {
  try {
    // 并行请求所有配置接口
    const [ponds, deviceTypes, statusOptions, controlModes] = await Promise.all([
      fetch('/api/v1/ponds').then(res => res.json()),
      fetch('/api/v1/device-types').then(res => res.json()),
      fetch('/api/v1/enums/device-status').then(res => res.json()),
      fetch('/api/v1/enums/control-modes').then(res => res.json())
    ]);

    // 渲染表单选项
    renderFormOptions({
      pondList: ponds.data,
      deviceTypeList: deviceTypes.data,
      statusList: statusOptions.data,
      controlModeList: controlModes.data
    });
  } catch (error) {
    console.error('加载配置数据失败:', error);
  }
}

// 当选择传感器类型时，额外加载传感器类型列表
async function onDeviceCategoryChange(category) {
  if (category === 'sensor') {
    const sensorTypes = await fetch('/api/v1/sensor-types').then(res => res.json());
    renderSensorTypeOptions(sensorTypes.data);
  }
}
```

### 设备列表筛选

```javascript
// 获取筛选条件的选项数据
async function initFilterOptions() {
  const [ponds, statusOptions, controlModes] = await Promise.all([
    fetch('/api/v1/ponds').then(res => res.json()),
    fetch('/api/v1/enums/device-status').then(res => res.json()),
    fetch('/api/v1/enums/control-modes').then(res => res.json())
  ]);

  // 渲染筛选下拉框
  renderFilterSelects({
    ponds: ponds.data,
    statuses: statusOptions.data,
    controlModes: controlModes.data
  });
}

// 应用筛选条件
function applyFilters(filters) {
  const params = new URLSearchParams({
    pond_id: filters.pondId,
    status: filters.status,
    control_mode: filters.controlMode,
    page: 1,
    page_size: 20
  });
  
  fetch(`/api/v1/devices?${params}`)
    .then(res => res.json())
    .then(data => renderDeviceList(data.data.items));
}
```

---

## 更新日志

### v1.0.0 (2026-01-14)
- 初始版本
- 实现设备列表查询、详情查看、新增、编辑、删除功能
- 支持多条件筛选和搜索
- 支持分页查询
- 支持根据设备类型动态提供扩展字段（sensors/feeders/cameras）
- 采用多表继承设计模式

