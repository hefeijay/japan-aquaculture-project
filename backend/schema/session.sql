-- 会话表 (Session Table)
-- 用于存储用户会话信息和配置

CREATE TABLE IF NOT EXISTS `session` (
    `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(128) NOT NULL UNIQUE COMMENT '会话唯一标识符',
    `user_id` VARCHAR(128) NOT NULL COMMENT '用户ID',
    `config` TEXT COMMENT '会话配置（JSON格式）',
    `status` VARCHAR(50) DEFAULT 'active' COMMENT '会话状态：active, inactive, archived',
    `session_name` VARCHAR(128) DEFAULT 'new chat' COMMENT '会话名称',
    `summary` VARCHAR(2048) DEFAULT NULL COMMENT '会话摘要',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_session_session_id` (`session_id`),
    INDEX `idx_session_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';

