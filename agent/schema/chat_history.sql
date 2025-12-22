-- 对话历史记录表
CREATE TABLE IF NOT EXISTS chat_history (
  id                 BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
  session_id        VARCHAR(128) NOT NULL COMMENT '会话ID',
  role              VARCHAR(16) NOT NULL COMMENT '角色：user 或 assistant',
  message           TEXT NOT NULL COMMENT '消息内容',
  intent            VARCHAR(64) NULL COMMENT '识别的意图',
  metadata          TEXT NULL COMMENT '额外信息（JSON格式）',
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  INDEX idx_chat_session_ts (session_id, created_at),
  INDEX idx_chat_created_at (created_at)
) COMMENT='对话历史记录表';

