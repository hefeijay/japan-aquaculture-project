# 传感器读数数据修复脚本使用说明

## 功能概述

`fix_sensor_readings_data.py` 用于修复 `sensor_readings` 表中错误的字段映射问题，主要包括：

1. **metric='temperature' 但 type_name 错误** - 温度字段应该使用对应传感器的 type_name，但 unit 为 '°C'
2. **metric='turbidity' 但 type_name 错误** - 浊度字段应该使用浊度传感器的 type_name
3. **metric='ph' 但 type_name 错误** - pH字段应该使用pH传感器的 type_name
4. **其他 metric 与 type_name 不匹配的情况**

## 问题原因

之前的代码在遍历传感器配置时，使用了错误的遍历顺序，导致：
- 不同传感器的数据使用了错误的配置
- 温度字段（ph_temperature, turbidity_temperature）被错误映射

## 修复逻辑

脚本会根据以下规则修复数据：

1. **从数据库获取正确配置**：通过 `sensor_id` 查询 `sensors` 表，获取对应的 `sensor_type`，从而确定正确的 `type_name` 和 `unit`

2. **温度字段特殊处理**：
   - `metric='temperature'` + `sensor_id` 对应 pH 传感器 → `type_name='pH传感器'`, `unit='°C'`
   - `metric='temperature'` + `sensor_id` 对应浊度传感器 → `type_name='浊度传感器'`, `unit='°C'`

3. **普通字段处理**：
   - 使用传感器类型对应的 `type_name` 和 `unit`

4. **description 字段修复**：
   - 格式：`{pool_id}号池 - {metric} - 批次{batch_id}`

## 使用方法

### 1. 干运行模式（推荐先执行）

```bash
# 只查找需要修复的记录，不实际修改数据库
cd /srv/japan_server
python scripts/fix_sensor_readings_data.py --dry-run
```

### 2. 实际执行修复

```bash
# 实际修复数据库记录（需要确认）
python scripts/fix_sensor_readings_data.py --execute
```

### 3. 只修复特定传感器

```bash
# 只修复 sensor_id=3 的记录
python scripts/fix_sensor_readings_data.py --execute --sensor-id 3
```

### 4. 只修复特定 metric

```bash
# 只修复 metric='temperature' 的记录
python scripts/fix_sensor_readings_data.py --execute --metric temperature
```

### 5. 组合使用

```bash
# 只修复 sensor_id=3 且 metric='temperature' 的记录
python scripts/fix_sensor_readings_data.py --execute --sensor-id 3 --metric temperature
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--dry-run` | 干运行模式，只查找不修复 | 默认开启 |
| `--execute` | 实际执行修复（需要明确指定） | False |
| `--sensor-id` | 只修复指定 sensor_id 的记录 | None（修复所有） |
| `--metric` | 只修复指定 metric 的记录 | None（修复所有） |

## 输出示例

### 干运行模式输出

```
============================================================
干运行模式：只查找需要修复的记录，不实际修改
============================================================
开始查找需要修复的记录...
共找到 1250 条有 metric 的记录
发现需要修复的记录 ID=123: sensor_id=3, metric=temperature, fixes={'type_name': ('PH', 'pH传感器'), 'unit': ('pH', '°C')}
发现需要修复的记录 ID=124: sensor_id=4, metric=temperature, fixes={'type_name': ('temperature', '浊度传感器'), 'unit': ('NTU', '°C')}
...
共找到 156 条需要修复的记录
[DRY-RUN] 将修复 156 条记录
```

### 执行模式输出

```
============================================================
执行模式：将实际修复数据库记录
============================================================
确认要继续吗？(yes/no): yes
开始查找需要修复的记录...
共找到 1250 条有 metric 的记录
共找到 156 条需要修复的记录
已修复 100 条记录...
已修复 156 条记录...
所有修复已提交，共修复 156 条记录
============================================================
修复完成统计
============================================================
总记录数: 156
成功修复: 156
修复失败: 0
跳过记录: 0
============================================================
```

## 日志文件

脚本运行日志会保存到：
- `logs/fix_sensor_readings.log` - 详细的修复日志

## 注意事项

1. **备份数据库**：在执行修复前，建议先备份数据库
   ```bash
   mysqldump -u root -p cognitive_center > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **先干运行**：建议先使用 `--dry-run` 模式查看需要修复的记录，确认无误后再执行

3. **分批修复**：如果记录数量很大，可以分批修复：
   ```bash
   # 先修复 sensor_id=3 的记录
   python scripts/fix_sensor_readings_data.py --execute --sensor-id 3
   
   # 再修复 sensor_id=4 的记录
   python scripts/fix_sensor_readings_data.py --execute --sensor-id 4
   ```

4. **验证修复结果**：修复后可以查询数据库验证：
   ```sql
   -- 检查 temperature 字段的修复情况
   SELECT sensor_id, metric, type_name, unit, COUNT(*) as count
   FROM sensor_readings
   WHERE metric = 'temperature'
   GROUP BY sensor_id, metric, type_name, unit;
   
   -- 检查 turbidity 字段的修复情况
   SELECT sensor_id, metric, type_name, unit, COUNT(*) as count
   FROM sensor_readings
   WHERE metric = 'turbidity'
   GROUP BY sensor_id, metric, type_name, unit;
   ```

## 故障排查

### 问题：找不到传感器记录
- 检查 `sensors` 表中是否存在对应的记录
- 检查 `sensor_id` 是否正确

### 问题：修复失败
- 查看日志文件获取详细错误信息
- 检查数据库连接是否正常
- 检查是否有外键约束冲突

### 问题：修复后数据仍然不对
- 确认修复脚本使用的配置是否正确
- 检查数据库中 `sensors` 和 `sensor_types` 表的数据是否正确

## 修复规则总结

| metric | sensor_id | 正确的 type_name | 正确的 unit |
|--------|-----------|------------------|-------------|
| temperature | 3 (pH传感器) | pH传感器 | °C |
| temperature | 4 (浊度传感器) | 浊度传感器 | °C |
| ph | 3 | pH传感器 | pH |
| turbidity | 4 | 浊度传感器 | NTU |
| do | 1 | 溶解氧传感器 | mg/L |
| water_level | 2 | 液位传感器 | mm |

## 相关文件

- 修复脚本：`scripts/fix_sensor_readings_data.py`
- 日志文件：`logs/fix_sensor_readings.log`
- 数据库模型：`db_models/sensor_reading.py`
- 数据库模型：`db_models/sensor.py`
- 数据库模型：`db_models/sensor_type.py`






















