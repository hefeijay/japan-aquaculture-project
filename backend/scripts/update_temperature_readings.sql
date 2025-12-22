-- 更新 sensor_readings 表中 value > 10 且 metric = 'temperature' 的记录
-- 将 type_name 设置为 'temperature'，description 设置为 '温度'

UPDATE sensor_readings
SET 
    type_name = 'temperature',
    description = '温度'
WHERE 
    value > 10 
    AND metric = 'temperature';

-- 查看更新前的记录数量（用于验证）
-- SELECT COUNT(*) as count_before_update
-- FROM sensor_readings
-- WHERE value > 10 AND metric = 'temperature';

-- 查看更新后的记录（用于验证）
-- SELECT id, sensor_id, value, metric, type_name, description, recorded_at
-- FROM sensor_readings
-- WHERE value > 10 AND metric = 'temperature'
-- LIMIT 10;


