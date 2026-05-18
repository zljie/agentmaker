#!/bin/bash
# 采购审批工作流演示启动脚本

echo "============================================"
echo "   采购审批 Agent 工作流演示"
echo "============================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
python3 -c "from app import app" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   安装依赖..."
    pip3 install -q -r requirements.txt
fi

echo "✅ 依赖检查完成"
echo ""
echo "============================================"
echo ""
echo "启动服务器: http://localhost:5011"
echo ""
echo "测试工作流示例:"
echo "  1. 打开浏览器访问 http://localhost:5011"
echo "  2. 在聊天框输入:"
echo "     '查询今日待审批的采购申请单，如果金额大于1000的需要人工审核'"
echo ""
echo "或者直接运行测试:"
echo "  PYTHONPATH=. python3 tests/test_procurement_workflow.py"
echo ""
echo "============================================"
echo ""

# 启动服务器
python3 app.py
