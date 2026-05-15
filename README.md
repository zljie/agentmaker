# NextStudio - AgentScope + FastHTML

本体驱动 Agent 构建平台 (Python 版本)

## 技术栈

- **FastHTML** - Python 原生 Web 框架，无需前端构建
- **AgentScope** - 智能体运行时 (agentscope-ai/agentscope)
- **Mock Connector** - 用于演示的模拟采购系统

## 快速开始

### 1. 安装依赖

```bash
cd agentmaker
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

服务启动后访问: http://localhost:5001

### 3. 开始使用

- 概览页 (`/`) - 查看平台资源统计
- 对话测试 (`/chat`) - 与 Agent 对话
- 本体管理 (`/ontology`) - 查看本体配置
- 意图配置 (`/intent`) - 管理意图识别规则
- 技能配置 (`/skill`) - 查看可用技能
- 连接器 (`/connector`) - 查看 Mock 连接器

## 项目结构

```
agentmaker/
├── app.py                 # FastHTML 应用入口
├── config.py              # 配置管理
├── requirements.txt       # 依赖
│
├── models/               # 数据模型
│   ├── ontology.py       # 本体定义
│   ├── intent.py         # 意图配置
│   ├── skill.py          # 技能定义
│   ├── connector.py      # 连接器 (含 Mock)
│   └── bundle.py         # Bundle 配置包
│
├── services/             # 服务层
│   ├── agentscope_runner.py  # AgentScope 封装
│   └── storage_service.py    # 存储服务
│
├── routes/               # FastHTML 路由
│   ├── api.py           # REST API
│   └── pages.py         # 页面路由
│
└── static/              # 静态资源
    ├── css/app.css      # 样式
    └── js/app.js        # 前端脚本
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/ontologies` | GET | 获取本体列表 |
| `/api/intents` | GET | 获取意图列表 |
| `/api/skills` | GET | 获取技能列表 |
| `/api/connectors` | GET | 获取连接器列表 |
| `/api/bundle` | GET | 获取 Bundle 配置 |
| `/api/runs` | POST | 创建运行 |
| `/api/runs/{id}/events` | GET | SSE 事件流 |
| `/api/runs/{id}/abort` | POST | 中止运行 |

## Mock Connector

Mock 连接器提供以下模拟数据:

- **物料查询** - 5 种物料主数据
- **供应商查询** - 4 家供应商
- **采购订单查询** - 订单列表
- **需求分析** - Top N 物料排名
- **供应商绩效** - 交付率分析

## 与 Verbal 集成

待补充部署配置

## License

Apache 2.0
