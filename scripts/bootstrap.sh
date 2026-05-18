#!/bin/bash
#
# NextStudio 规范快速初始化脚本
# 用法: curl -sL <raw_url> | bash
# 或:   bash <(curl -sL <raw_url>)
#

set -e

STANDARDS_REPO="${STANDARDS_REPO:-https://github.com/your-org/nextstudio-standards.git}"
STANDARDS_BRANCH="${STANDARDS_BRANCH:-main}"

echo "=========================================="
echo " NextStudio 规范快速初始化"
echo "=========================================="
echo ""

# 检测是否已存在 .specify
if [ -d ".specify" ]; then
    echo "[WARN] .specify 目录已存在，跳过初始化"
    echo "       如需重新初始化，请先删除 .specify 目录"
    exit 0
fi

# 1. 初始化 Spec Kit (如果没有)
if ! command -v specify &> /dev/null; then
    echo "[1/4] 安装 Specify CLI..."
    if command -v uvx &> /dev/null; then
        uvx --from git+https://github.com/github/spec-kit.git specify --version
    else
        echo "  请先安装 uv: https://astral.sh/uv/"
        exit 1
    fi
else
    echo "[1/4] Specify CLI 已安装"
fi

# 2. 初始化 Spec Kit 项目结构
echo "[2/4] 初始化 Spec Kit 项目结构..."
if command -v uvx &> /dev/null; then
    uvx --from git+https://github.com/github/spec-kit.git specify init . --integration generic --here --force 2>/dev/null || true
else
    specify init . --integration generic --here --force 2>/dev/null || true
fi

# 3. 下载规范模板
echo "[3/4] 下载项目规范..."
if command -v git &> /dev/null && git ls-remote "$STANDARDS_REPO" &> /dev/null; then
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 -b "$STANDARDS_BRANCH" "$STANDARDS_REPO" "$TEMP_DIR/standards" 2>/dev/null || true
    
    # 复制规范文件
    if [ -f "$TEMP_DIR/standards/.specify/memory/constitution.md" ]; then
        mkdir -p .specify/memory
        cp "$TEMP_DIR/standards/.specify/memory/constitution.md" .specify/memory/
        echo "  [OK] constitution.md"
    fi
    
    # 复制文档模板
    if [ -f "$TEMP_DIR/standards/templates/SPEC.md.tmpl" ]; then
        cp "$TEMP_DIR/standards/templates/SPEC.md.tmpl" SPEC.md 2>/dev/null || true
        echo "  [OK] SPEC.md"
    fi
    
    if [ -f "$TEMP_DIR/standards/templates/plan.md.tmpl" ]; then
        cp "$TEMP_DIR/standards/templates/plan.md.tmpl" plan.md 2>/dev/null || true
        echo "  [OK] plan.md"
    fi
    
    rm -rf "$TEMP_DIR"
else
    echo "  [SKIP] 规范仓库不可用，跳过下载"
fi

# 4. 创建基础文档（如果不存在）
echo "[4/4] 创建基础文档..."
[ ! -f "SPEC.md" ] && cat > SPEC.md << 'EOF'
# 项目技术文档

> 创建日期: $(date +%Y-%m-%d)
> 规范版本: 基于 nextstudio-standards

## 待补充

- 系统架构拓扑
- 模块说明
- API 文档
EOF
echo "  [OK] SPEC.md (待完善)"

[ ! -f "plan.md" ] && cat > plan.md << 'EOF'
# 项目迭代面板

## Backlog (待办)

## In Progress (进行中)

## Done (已完成)
EOF
echo "  [OK] plan.md (待完善)"

echo ""
echo "=========================================="
echo " 初始化完成!"
echo "=========================================="
echo ""
echo "下一步:"
echo "  1. 编辑 SPEC.md 完善技术文档"
echo "  2. 使用 /speckit.constitution 自定义规范"
echo "  3. 开始开发!"
echo ""
