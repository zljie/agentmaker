#!/bin/bash
# NextStudio 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║         NextStudio - AgentScope + FastHTML            ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. 检测 Python
echo -e "${YELLOW}[1/3]${NC} 检测 Python 环境..."
if command -v python3 &>/dev/null; then
    PYTHON=$(command -v python3)
elif command -v python &>/dev/null; then
    PYTHON=$(command -v python)
else
    echo -e "${RED}✗ 未找到 Python，请先安装 Python 3.9+${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} 使用: $PYTHON ($($PYTHON --version))"

# 2. 安装依赖
echo -e "${YELLOW}[2/3]${NC} 安装依赖..."
if ! $PYTHON -m pip install -q -r requirements.txt 2>/dev/null; then
    echo -e "${RED}✗ 依赖安装失败，尝试使用 pip3...${NC}"
    pip3 install -r requirements.txt
fi
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 3. 启动服务
echo -e "${YELLOW}[3/3]${NC} 启动服务..."

# 读取配置中的端口
PORT=$($PYTHON -c "import sys; sys.path.insert(0, '.'); from config import PORT; print(PORT)" 2>/dev/null || echo "5001")

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}║   NextStudio 启动成功                               ║${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}║   🌐 http://localhost:${PORT}                        ║${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}║   页面清单:                                          ║${NC}"
echo -e "${GREEN}║   · /           概览                                 ║${NC}"
echo -e "${GREEN}║   · /ontology   本体管理                            ║${NC}"
echo -e "${GREEN}║   · /intent     意图配置                            ║${NC}"
echo -e "${GREEN}║   · /skill      技能配置                            ║${NC}"
echo -e "${GREEN}║   · /connector  连接器                              ║${NC}"
echo -e "${GREEN}║   · /agent      Agent 构建                           ║${NC}"
echo -e "${GREEN}║   · /chat       对话测试                            ║${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

$PYTHON app.py
