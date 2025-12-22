-- 为 ponds 表添加 area 和 count 字段
-- 执行方式: mysql -u用户名 -p数据库名 < add_pond_fields.sql

-- 添加 area 字段（面积，单位：平方米）
ALTER TABLE ponds 
ADD COLUMN area FLOAT NULL COMMENT '养殖池实际面积（平方米）' 
AFTER location;

-- 添加 count 字段（实际统计数量，单位：尾数）
ALTER TABLE ponds 
ADD COLUMN count INT NULL COMMENT '养殖池实际统计的数量（尾数）' 
AFTER area;

-- 查看表结构确认
-- DESCRIBE ponds;

