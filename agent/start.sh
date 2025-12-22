#!/bin/bash
# ============================================
# 启动 LangGraph 后端服务
# ============================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}启动 LangGraph 后端服务${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}错误: 未找到 python3${NC}"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
pip install -r requirements.txt

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: 未找到 .env 文件，请创建并配置环境变量${NC}"
    echo -e "${YELLOW}可以参考以下配置：${NC}"
    echo "MYSQL_HOST=localhost"
    echo "MYSQL_PORT=3306"
    echo "MYSQL_USER=root"
    echo "MYSQL_PASSWORD=your_password"
    echo "MYSQL_DATABASE=aquaculture"
    echo "OPENAI_API_KEY=your_openai_api_key"
fi

# 创建日志目录
mkdir -p logs

# 启动服务
echo -e "${GREEN}启动服务...${NC}"
# 使用配置中的端口（默认8000），支持HTTP和WebSocket
python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --reload

