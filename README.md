# NextStudio - AgentScope + FastHTML

本体驱动 Agent 构建平台

## 技术栈

- **FastHTML** - Python 原生 Web 框架，无需前端构建
- **AgentScope** - 智能体运行时 (agentscope-ai/agentscope)
- **DeepSeek** - LLM 模型支持 (deepseek-chat)
- **Supabase** - PostgreSQL 元数据存储 (可选)

## 快速开始

### 1. 安装依赖

```bash
cd agentmaker
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 服务器配置
HOST=0.0.0.0
PORT=5001
DEBUG=true

# LLM 配置
LLM_MODEL_NAME=deepseek-chat
LLM_API_KEY=sk-your-api-key  # 需要设置才能使用真实 LLM
LLM_API_BASE=https://api.deepseek.com/v1

# 数据库配置 (可选)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-supabase-key
```

### 3. 启动服务

```bash
python app.py
```

服务启动后访问: http://localhost:5001

### 4. 开始使用

- 概览页 (`/`) - 查看平台资源统计
- 对话测试 (`/chat`) - 与 Agent 对话
- 本体管理 (`/ontology`) - 查看和上传本体配置
- 意图配置 (`/intent`) - 管理意图识别规则
- 技能配置 (`/skill`) - 查看可用技能
- 连接器 (`/connector`) - 查看 Mock 连接器
- 采购审批 (`/approvals`) - 采购申请审批

## 项目结构

```
agentmaker/
├── app.py                     # FastHTML 应用入口
├── config.py                  # 配置管理
├── requirements.txt           # Python 依赖
│
├── models/                    # 数据模型
│   ├── ontology.py           # 本体定义
│   ├── intent.py             # 意图配置
│   ├── skill.py              # 技能定义
│   ├── connector.py          # 连接器 (含 Mock)
│   └── bundle.py             # Bundle 配置包
│
├── services/                  # 服务层
│   ├── agentscope_runner.py  # AgentScope 封装
│   ├── procurement_workflow.py # 采购审批工作流
│   ├── storage_service.py    # 存储服务
│   ├── ontology_parser.py    # 本体解析器
│   ├── knowledge_graph.py    # 知识图谱
│   ├── osi_parser.py         # OSI 解析器
│   └── database.py          # 数据库服务
│
├── routes/                    # FastHTML 路由
│   ├── api.py               # REST API
│   └── pages.py             # 页面路由
│
├── configs/                   # 配置文件
│   ├── ontology_procurement.py
│   ├── intents_procurement.py
│   └── skills_procurement.py
│
├── static/                   # 静态资源
│   ├── css/app.css          # 样式
│   └── js/app.js           # 前端脚本
│
├── supabase/                 # Supabase 配置
│   ├── config.toml
│   └── migrations/
│
├── tests/                    # 测试
│   └── test_procurement_workflow.py
│
└── configs/                  # 部署配置
    ├── railway.json         # Railway 部署
    └── render.yaml          # Render 部署
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/ontologies` | GET | 获取本体列表 |
| `/api/ontologies/current` | GET | 获取当前本体详情 |
| `/api/ontologies/upload` | POST | 上传本体 |
| `/api/ontologies/parse` | POST | 解析本体 |
| `/api/intents` | GET/POST | 获取/创建意图 |
| `/api/intents/{type}` | PUT/DELETE | 更新/删除意图 |
| `/api/skills` | GET | 获取技能列表 |
| `/api/connectors` | GET | 获取连接器列表 |
| `/api/bundle` | GET | 获取 Bundle 配置 |
| `/api/runs` | GET/POST | 运行历史/创建运行 |
| `/api/runs/{id}` | GET | 获取运行详情 |
| `/api/runs/{id}/events` | GET | SSE 事件流 |
| `/api/runs/{id}/abort` | POST | 中止运行 |
| `/api/approvals/pending` | GET | 待审批列表 |
| `/api/approvals/history` | GET | 审批历史 |
| `/api/approvals` | POST | 提交审批 |
| `/api/approvals/{request_no}` | GET | 申请单详情 |

## 核心功能

### 1. 本体管理

上传和解析采购领域本体，支持 OSI 标准格式。

### 2. 意图识别

基于规则的意图分类，支持采购场景的多种查询和操作意图。

### 3. 智能体运行

- **Mock Runner**: 不依赖 LLM API，用于演示和测试
- **AgentScope Runner**: 真实 LLM 驱动，需要配置 DeepSeek API Key

### 4. 采购审批工作流

- 金额 ≤ 1000 元：自动审批
- 金额 > 1000 元：人工审批 (HITL)
- 支持单行项审批

### 5. Mock Connector

提供以下模拟数据:

- **物料查询** - 5 种物料主数据
- **供应商查询** - 4 家供应商
- **采购订单查询** - 订单列表
- **需求分析** - Top N 物料排名
- **供应商绩效** - 交付率分析

## 部署

### Railway

```bash
# 使用 railway.json 配置
railway up
```

### Render

```bash
# 使用 render.yaml 配置
render blueprint apply
```

## License

Apache 2.0
