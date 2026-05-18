# NextStudio Standards

> NextStudio 项目的开发规范和模板集合，基于 [johnosn-sdd-script](https://github.com/zljie/johnosn-sdd-script)

## 快速开始

### 在新项目中引入规范

```bash
# 方式 A: Git Submodule (推荐)
git submodule add https://github.com/zljie/johnosn-sdd-script.git .sdd-standards
ln -s .sdd-standards/.specify .specify
cp .sdd-standards/plan.md .
cp .sdd-standards/templates/SPEC.md.tmpl SPEC.md

# 方式 B: 直接复制
git clone https://github.com/zljie/johnosn-sdd-script.git /tmp/sdd-standards
cp -r /tmp/sdd-standards/.specify .
cp /tmp/sdd-standards/plan.md .
cp /tmp/sdd-standards/templates/SPEC.md.tmpl SPEC.md

# 方式 C: 一键初始化 (需要网络)
curl -sL https://raw.githubusercontent.com/zljie/johnosn-sdd-script/main/scripts/bootstrap.sh | bash
```

## 包含内容

### 1. Constitution (项目规范)

`.specify/memory/constitution.md` - 核心开发原则：

- **Result-Oriented** - 结果导向，获得关键信息立即汇报
- **No Busy-Wait** - 禁止无效轮询，15秒无进展请求人工介入
- **Read Before Act** - 调研先行，禁止盲目操作
- **Token Saving** - 上下文精简，超20行日志需筛选
- **Skip COT** - 标准运维跳过复杂思维链

### 2. 文档模板

| 文件 | 用途 |
|------|------|
| `SPEC.md.tmpl` | 系统技术文档模板 |
| `plan.md.tmpl` | 敏捷迭代面板模板 |

### 3. 初始化脚本

`bootstrap.sh` - 一键初始化规范

### 4. Presets (预设)

| Preset | 说明 |
|--------|------|
| `karpathy-rules` | 自动注入 Karpathy 编码准则到 `.cursor/rules/` |

**karpathy-rules 包含内容**（来源：[multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)）：
- Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution

**安装方式**：
```bash
mkdir -p .specify/presets
ln -s /path/to/johnosn-sdd-script/presets/karpathy-rules .specify/presets/
```

## 自定义规范

### 修改 Constitution

编辑 `.specify/memory/constitution.md` 添加自定义规则：

```markdown
### VI. 我的自定义规则
[你的规范内容]
```

### 创建 Preset

如需团队级定制，创建 Preset：

```bash
specify preset create my-preset
```

## 与 Spec Kit 集成

本仓库与 [github/spec-kit](https://github.com/github/spec-kit) 无缝集成：

```bash
# 初始化 Spec Kit
specify init . --integration cursor-agent

# 使用规范命令
/speckit.constitution  # 编辑项目原则
/speckit.specify       # 定义需求
/speckit.plan          # 制定计划
/speckit.tasks         # 拆分任务
/speckit.implement     # 执行实现
```

## License

MIT
