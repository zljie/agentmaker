# 项目结构规范

## 目录结构

```
agentmaker/
├── app.py                 # 应用入口，初始化 FastHTML 应用
├── config.py              # 配置管理
├── requirements.txt       # 依赖声明
│
├── models/                # 数据模型层
│   ├── __init__.py       # 模型导出
│   ├── ontology.py       # 本体定义
│   ├── intent.py         # 意图配置
│   ├── skill.py          # 技能定义
│   ├── connector.py      # 连接器配置
│   └── bundle.py         # Bundle 配置
│
├── services/              # 服务层
│   ├── __init__.py       # 服务导出
│   ├── agentscope_runner.py  # AgentScope 运行时
│   └── storage_service.py    # 存储服务
│
├── routes/                # 路由层
│   ├── __init__.py       # 路由导出
│   ├── api.py            # REST API
│   └── pages.py          # 页面路由
│
├── static/                # 静态资源
│   ├── css/
│   │   └── app.css       # 样式
│   └── js/
│       └── app.js        # 前端脚本
│
├── templates/             # 模板目录
├── utils/                 # 工具函数
├── SDK/                   # SDK 相关
├── __init__.py           # 包初始化
└── start.sh              # 启动脚本
```

## 各层职责

### models/ - 数据模型层

负责数据结构和业务对象的定义。

| 文件 | 说明 |
|------|------|
| `ontology.py` | 定义本体：EntitySpec, ActionSpec, OntologySpec |
| `intent.py` | 意图识别：IntentSpec, IntentClassification |
| `skill.py` | 技能定义：SkillSpec, SkillRegistry |
| `connector.py` | 连接器：ConnectorConfig, ConnectorAction |
| `bundle.py` | Bundle 打包：Bundle, AgentConfig, RuntimeConfig |

### services/ - 服务层

负责业务逻辑和外部服务交互。

| 文件 | 说明 |
|------|------|
| `agentscope_runner.py` | 封装 AgentScope 运行时 |
| `storage_service.py` | 数据持久化服务 |

### routes/ - 路由层

负责 HTTP 请求处理和响应。

| 文件 | 说明 |
|------|------|
| `api.py` | REST API 端点 |
| `pages.py` | 页面路由 |

## 新增文件规范

### 新增模型
1. 在 `models/` 创建新文件，如 `new_model.py`
2. 定义数据类
3. 在 `models/__init__.py` 中添加导出

### 新增服务
1. 在 `services/` 创建新文件，如 `new_service.py`
2. 实现服务逻辑
3. 在 `services/__init__.py` 中添加导出

### 新增路由
1. API 路由添加到 `routes/api.py`
2. 页面路由添加到 `routes/pages.py`

### 新增工具
1. 在 `utils/` 创建工具文件
2. 或在对应的功能目录下创建

## 模块间依赖

```
app.py
├── config.py
├── models/           # ← 无上层依赖
├── services/         # ← 依赖 models
│   └── models/
├── routes/           # ← 依赖 models, services
│   ├── models/
│   └── services/
└── utils/            # ← 无依赖
```

**规则**：
- 依赖方向只能向下（外层依赖内层）
- models 层不能依赖其他业务模块
- services 层只能依赖 models
- routes 层可以依赖 models 和 services

## 配置管理

所有配置集中在 `config.py`，包括：
- 服务端口
- 数据库连接
- AgentScope 配置
- Mock Connector 设置

## 静态资源

| 目录 | 说明 |
|------|------|
| `static/css/` | CSS 样式文件 |
| `static/js/` | JavaScript 文件 |
| `templates/` | FastHTML 模板文件 |
