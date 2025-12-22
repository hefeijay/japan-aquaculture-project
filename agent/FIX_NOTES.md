# 数据库字段不匹配问题修复说明

## 问题描述

错误信息：
```
Unknown column 'sensor_readings.device_id' in 'field list'
```

## 原因分析

1. **模型定义**：使用 `device_id` 字段
2. **实际数据库表**：使用 `sensor_id` 字段
3. **不匹配**：导致 SQL 查询失败

## 解决方案

### 方案一：修改模型匹配实际表结构（已实施）

已修改 `models/sensor_reading.py`：
- 将 `device_id` 改为 `sensor_id`
- 添加 `device_id` 属性作为兼容层（映射到 `sensor_id`）
- 支持 `recorded_at` 和 `ts_utc` 两个时间字段
- 支持 `type_name`、`description` 等快照字段

**优点**：
- 快速修复，无需修改数据库
- 保持向后兼容

**缺点**：
- 模型与新的 schema 设计不一致
- 需要维护兼容层

### 方案二：执行数据库迁移（推荐长期方案）

如果需要使用新的 `device_id` 字段设计，可以执行迁移脚本：

```sql
-- 添加 device_id 字段
ALTER TABLE sensor_readings 
ADD COLUMN device_id BIGINT UNSIGNED NULL COMMENT '设备ID（FK）' AFTER sensor_id;

-- 从 sensor_id 迁移数据到 device_id（需要建立映射关系）
UPDATE sensor_readings sr
INNER JOIN sensors s ON sr.sensor_id = s.id
INNER JOIN devices d ON d.device_id = s.device_id  -- 需要建立映射
SET sr.device_id = d.device_id;

-- 设置 device_id 为 NOT NULL（迁移完成后）
ALTER TABLE sensor_readings 
MODIFY COLUMN device_id BIGINT UNSIGNED NOT NULL;

-- 添加外键约束
ALTER TABLE sensor_readings 
ADD CONSTRAINT fk_sr_device FOREIGN KEY (device_id) REFERENCES devices(device_id);
```

## 当前状态

✅ **已修复**：
- 模型定义已更新为使用 `sensor_id`
- 添加了 `device_id` 兼容属性
- 更新了查询逻辑以支持 `ts_utc` 和 `recorded_at`
- 对话接口已更新以使用正确的字段

## 测试

运行以下命令测试修复：

```bash
cd /srv/japan-aquaculture-project/backend

# 测试模型导入
python3 -c "from models.sensor_reading import SensorReading; print('OK')"

# 测试数据库查询
python3 -c "
from database import get_db
from models.sensor_reading import SensorReading
with get_db() as db:
    count = db.query(SensorReading).count()
    print(f'记录数: {count}')
"

# 测试对话接口
python3 test_chat.py "查询最近的水温数据"
```

## 注意事项

1. **字段映射**：
   - `sensor_id` → 实际数据库字段
   - `device_id` → 兼容属性（返回 `sensor_id` 的值）

2. **时间字段**：
   - `recorded_at` → 原始时间戳
   - `ts_utc` → UTC 时间戳（如果存在）
   - 查询时优先使用 `ts_utc`，如果为空则使用 `recorded_at`

3. **单位字段**：
   - `unit` → 单位（varchar(50)）
   - `type_name` → 传感器类型名称快照

## 后续建议

如果计划迁移到新的 schema 设计：
1. 执行数据库迁移脚本添加 `device_id` 字段
2. 建立 `sensors` 到 `devices` 的映射关系
3. 迁移数据
4. 更新模型定义使用 `device_id`
5. 移除兼容层

