# NextStudio Agent 指令

## 项目概述

**NextStudio** 是一个本体驱动的 Agent 构建平台，基于 FastHTML + AgentScope 构建。

### 核心技术栈
- **FastHTML** - Python 原生 Web 框架
- **AgentScope** - 智能体运行时
- **本体驱动** - 通过 ontology/intent/skill/connector 配置驱动 Agent

## 开发规范

### 代码组织
```
agentmaker/
├── app.py           # FastHTML 应用入口
├── config.py        # 配置管理
├── models/          # 数据模型层
├── services/        # 服务层
├── routes/          # 路由层 (api.py, pages.py)
├── static/          # 静态资源
└── utils/           # 工具函数
```

### 模型层职责
- `models/ontology.py` - 本体定义 (EntitySpec, ActionSpec, OntologySpec)
- `models/intent.py` - 意图识别配置
- `models/skill.py` - 技能定义与注册
- `models/connector.py` - 连接器配置 (包含 Mock Connector)
- `models/bundle.py` - Bundle 配置包

### 服务层职责
- `services/agentscope_runner.py` - AgentScope 运行时封装
- `services/storage_service.py` - 存储服务

### 路由层职责
- `routes/api.py` - REST API 路由
- `routes/pages.py` - 页面路由

## 开发指南

### 添加新的模型类
1. 在 `models/` 目录创建或编辑模型文件
2. 使用 dataclass 或 pydantic 定义数据模型
3. 在 `models/__init__.py` 中导出

### 添加新的 API 端点
1. 在 `routes/api.py` 中添加路由函数
2. 返回 JSON 响应，使用 FastHTML 的 jsonify 或直接返回 dict

### 添加新的页面
1. 在 `routes/pages.py` 中添加页面路由
2. 使用 FastHTML 的组件函数返回 HTML

### 添加新服务
1. 在 `services/` 目录创建服务文件
2. 在 `services/__init__.py` 中导出

## 配置管理

### config.py
- 集中管理所有配置项
- 支持环境变量覆盖
- 不在代码中硬编码敏感信息

## API 设计规范

### REST API 约定
- 使用名词复数形式：`/api/runs`, `/api/ontologies`
- 使用标准 HTTP 方法：GET（查询）、POST（创建）、PUT（更新）、DELETE（删除）
- 返回统一的 JSON 格式

### SSE 事件流
- 长连接使用 Server-Sent Events
- 事件格式：`data: {json}\n\n`
- 支持 abort 终止

## Mock Connector

Mock Connector 提供模拟采购系统数据：
- 物料查询
- 供应商查询
- 采购订单查询
- 需求分析
- 供应商绩效

开发时可用于测试和演示。

## 代码风格

- 使用 Python 3.10+ 语法
- 类型注解是可选的但推荐使用
- 遵循 PEP 8 规范
- 简洁的 docstring 说明功能

## 调试和测试

### 本地运行
```bash
python app.py
```

服务运行在 http://localhost:5001

### API 测试
- `/api/health` - 健康检查
- `/chat` - 对话测试页面
