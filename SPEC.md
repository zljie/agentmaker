# NextStudio 技术文档

> 本文档记录 NextStudio 系统的技术架构、模块拓扑和核心实现。
> 每次任务完成后请检查并更新此文档，保持与项目架构一致。

---

## 1. 系统架构拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NextStudio                                      │
│                     本体驱动 Agent 构建平台                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │   Frontend   │ │   Backend    │ │   Runtime    │
            │  (FastHTML)  │ │   (API)      │ │ (AgentScope) │
            └──────────────┘ └──────────────┘ └──────────────┘
                    │                │                │
         ┌──────────┼──────────┐      │         ┌─────┼─────┐
         │          │          │      │         │     │     │
         ▼          ▼          ▼      ▼         ▼     ▼     ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   ┌─────────┐
    │  Pages  │ │ Static  │ │  Routes │ │ Services │   │ Connectors│
    │(pages.py)│ │(css/js) │ │ (api.py)│ │(runner)  │   │(Mock/SAP)│
    └─────────┘ └─────────┘ └─────────┘ └─────────┘   └─────────┘
```

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **Web 框架** | FastHTML | Python 原生 Web 框架，无需前端构建 |
| **Agent 运行时** | AgentScope | agentscope-ai/agentscope 智能体运行时 |
| **LLM 集成** | DeepSeek API | 支持 deepseek-chat 模型 |
| **异步框架** | asyncio | 流式 SSE 事件输出 |
| **数据库** | Supabase (可选) | PostgreSQL 元数据存储 |
| **前端样式** | Tailwind CSS | CDN 引入，无需构建 |
| **图标** | Font Awesome 6 | CDN 引入 |
| **配置管理** | .env | 环境变量配置 |

---

## 3. 模块拓扑

### 3.1 应用入口

| 文件 | 路径 | 说明 |
|------|------|------|
| 应用入口 | `app.py` | FastHTML 应用创建，路由注册 |
| 配置管理 | `config.py` | 环境变量、LLM 配置、服务端口 |

**核心片段：**

```python
# app.py - 创建 FastHTML 应用
app = FastHTML(
    title="NextStudio",
    debug=DEBUG,
    hdrs=(Link(rel="stylesheet", href="/static/css/app.css"),),
)
api_routes(app)
page_routes(app)
```

```python
# config.py - LLM 配置
LLM_CONFIG = {
    "model_name": os.getenv("LLM_MODEL_NAME", "deepseek-chat"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "api_base": os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1"),
}
```

---

### 3.2 路由层 (routes/)

| 文件 | 路径 | 说明 |
|------|------|------|
| 页面路由 | `routes/pages.py` | 渲染前端页面（概览、本体、意图、技能等） |
| API 路由 | `routes/api.py` | RESTful API（本体、意图、运行管理、审批） |

**核心片段：**

```python
# routes/pages.py - 页面渲染函数
def render_layout(title: str, active_tab: str, content: str) -> Table:
    """渲染页面布局 - 包含侧边栏、头部、内容区"""

def render_overview() -> str:
    """概览页 - 显示资源统计卡片"""

def render_ontology() -> str:
    """本体管理页 - 列表和上传功能"""

def render_intent() -> str:
    """意图配置页 - CRUD 操作"""
```

```python
# routes/api.py - API 路由
@app.route("/api/health")           # 健康检查
@app.route("/api/ontologies")       # 本体列表/创建
@app.route("/api/ontologies/upload") # 本体上传
@app.route("/api/intents")          # 意图 CRUD
@app.route("/api/skills")           # 技能列表
@app.route("/api/connectors")       # 连接器列表
@app.route("/api/runs")             # 运行管理 (创建/列表)
@app.route("/api/runs/{id}/events") # SSE 流式事件
@app.route("/api/approvals")        # 采购审批
```

---

### 3.3 数据模型层 (models/)

| 文件 | 路径 | 说明 |
|------|------|------|
| 本体模型 | `models/ontology.py` | 本体定义（实体、属性、操作） |
| 意图模型 | `models/intent.py` | 意图定义和路由 |
| 技能模型 | `models/skill.py` | 技能定义和注册表 |
| 连接器模型 | `models/connector.py` | 连接器配置和 Mock 实现 |
| Bundle | `models/bundle.py` | 运行时配置包（聚合所有组件） |

**核心片段：**

```python
# models/ontology.py - 本体数据结构
@dataclass
class EntitySpec:
    name: str           # 实体名称
    description: str    # 描述
    labels: List[str]  # 标签
    dataset: str       # 数据集引用
    properties: List[PropertySpec]  # 属性列表

@dataclass
class ActionSpec:
    id: str            # 操作 ID
    name: str          # 操作名称
    kind: str          # 类型 (query/action)
    operation: str     # 操作类型
    entity_name: str   # 关联实体
```

```python
# models/bundle.py - Bundle 聚合组件
@dataclass
class Bundle:
    ontology: OntologySpec           # 本体
    intents: List[IntentSpec]        # 意图列表
    skills: List[SkillSpec]          # 技能列表
    connectors: List[ConnectorConfig] # 连接器列表
    agent_config: AgentConfig        # Agent 配置
    runtime: RuntimeConfig           # 运行时配置

    def build_system_prompt(self) -> str:
        """构建 System Prompt 用于 LLM"""
```

---

### 3.4 服务层 (services/)

| 文件 | 路径 | 说明 |
|------|------|------|
| AgentScope Runner | `services/agentscope_runner.py` | Agent 运行器，支持 Mock 和真实 LLM |
| 采购工作流 | `services/procurement_workflow.py` | 采购审批工作流引擎 |
| 存储服务 | `services/storage_service.py` | 运行状态存储（SSE 事件） |
| 本体解析器 | `services/ontology_parser.py` | LLM 驱动的本体解析 |
| 知识图谱 | `services/knowledge_graph.py` | 本体知识图谱构建 |
| OSI 解析器 | `services/osi_parser.py` | OSI 格式解析和转换 |
| 数据库服务 | `services/database.py` | Supabase 数据库操作 |

**核心片段：**

```python
# services/agentscope_runner.py - Agent 运行器
class AgentScopeRunner:
    """真实 LLM 运行器 - 需要配置 API Key"""
    async def run_stream(self, user_message: str) -> AsyncGenerator[RunEvent, None]:
        # 1. 意图识别
        # 2. 创建 AgentScope ReActAgent
        # 3. 流式返回结果

class MockRunner:
    """Mock 运行器 - 不依赖 LLM API，用于演示"""
    async def run_stream(self, user_message: str) -> AsyncGenerator[RunEvent, None]:
        # 1. 意图识别
        # 2. 检测采购审批场景
        # 3. 模拟分步执行
        # 4. 自动审批 / HITL 审批
```

```python
# services/procurement_workflow.py - 采购工作流引擎
class ProcurementWorkflowEngine:
    """工作流程:
    1. 日期解析（内部函数） -> 减少 LLM token
    2. 意图识别
    3. 任务规划
    4. 分步执行
    5. 自动审批 / HITL 处理"""

    def convert_date_reference(self, text: str) -> DateRange:
        """基础技能：日期转换（内部函数，不消耗 token）"""

    def analyze_requests(self, requests: List[Dict]) -> Dict:
        """分析申请单，决定审批方式（自动 vs 人工）"""
        # 阈值: 1000 元以下自动审批
```

---

### 3.5 配置文件 (configs/)

| 文件 | 路径 | 说明 |
|------|------|------|
| 采购本体 | `configs/ontology_procurement.py` | 采购领域本体 YAML |
| 采购意图 | `configs/intents_procurement.py` | 采购意图定义 |
| 采购技能 | `configs/skills_procurement.py` | 采购技能定义 |

---

### 3.6 静态资源 (static/)

| 文件 | 路径 | 说明 |
|------|------|------|
| 样式 | `static/css/app.css` | 自定义样式 |
| 脚本 | `static/js/app.js` | 前端交互逻辑 |

---

## 4. API 接口文档

### 4.1 健康检查

```
GET /api/health

Response:
{
  "status": "ok",
  "service": "NextStudio",
  "version": "0.1.0",
  "llm_configured": true,
  "llm_model": "deepseek-chat",
  "database_connected": false
}
```

### 4.2 本体管理

```
GET  /api/ontologies           # 获取本体列表
GET  /api/ontologies/current   # 获取当前本体详情
POST /api/ontologies/upload    # 上传本体 (multipart/form-data)
POST /api/ontologies/parse     # 解析本体，提取意图
GET  /api/ontologies/knowledge-graph  # 获取知识图谱
```

### 4.3 意图管理

```
GET    /api/intents            # 获取意图列表
POST   /api/intents            # 创建意图
PUT    /api/intents/{type}     # 更新意图
DELETE /api/intents/{type}     # 删除意图
```

### 4.4 运行管理

```
GET  /api/runs                 # 获取运行历史
POST /api/runs                 # 创建运行
GET  /api/runs/{id}            # 获取运行详情
GET  /api/runs/{id}/events     # SSE 流式事件
POST /api/runs/{id}/abort      # 中止运行
```

### 4.5 采购审批

```
GET    /api/approvals/pending      # 获取待审批列表
GET    /api/approvals/history      # 获取审批历史
POST   /api/approvals              # 提交审批结果
GET    /api/approvals/{request_no} # 获取申请单详情
POST   /api/approvals/line         # 审批单个明细行
```

---

## 5. 关键流程

### 5.1 Agent 对话流程

```
用户输入
    │
    ▼
┌─────────────┐
│ 意图识别    │ ◄─── IntentRouter.classify()
└─────────────┘
    │
    ▼
┌─────────────┐
│ 任务规划    │ ◄─── MockRunner / AgentScopeRunner
└─────────────┘
    │
    ├───► 检测采购审批场景 ──► ProcurementWorkflowEngine
    │                              │
    │                         ┌────┴────┐
    │                         ▼         ▼
    │                   自动审批    HITL 审批
    │                   (≤1000元)   (>1000元)
    │
    └───► 模拟工具调用 ──► MockConnector
                               │
                          ┌────┴────┐
                          ▼         ▼
                    物料/供应商/订单
```

### 5.2 本体上传流程

```
上传文件 (YAML/JSON)
    │
    ▼
┌─────────────┐
│ 格式检测    │ ◄─── is_osi_format()
└─────────────┘
    │
    ├───► OSI 格式 ──► parse_osi_yaml() ──► convert_to_yaml()
    │
    ▼
┌─────────────┐
│ 解析验证    │ ◄─── OntologySpec.from_yaml()
└─────────────┘
    │
    ▼
┌─────────────┐
│ 数据库存储  │ ◄─── DatabaseService.create_ontology()
└─────────────┘
```

---

## 6. 配置说明

### 6.1 环境变量 (.env)

```bash
# 服务器配置
HOST=0.0.0.0
PORT=5011
DEBUG=true

# LLM 配置
LLM_MODEL_NAME=deepseek-chat
LLM_API_KEY=sk-xxxxx  # 需要设置才能使用真实 LLM
LLM_API_BASE=https://api.deepseek.com/v1

# 数据库配置 (可选)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
```

### 6.2 启动方式

```bash
# 开发模式
python app.py

# 服务启动在 http://localhost:5011
```

---

## 7. 目录结构

```
agentmaker/
├── app.py                     # FastHTML 应用入口
├── config.py                  # 配置管理
├── requirements.txt           # Python 依赖
│
├── models/                    # 数据模型
│   ├── ontology.py            # 本体定义
│   ├── intent.py              # 意图配置
│   ├── skill.py               # 技能定义
│   ├── connector.py           # 连接器 (含 Mock)
│   └── bundle.py              # Bundle 配置包
│
├── services/                  # 服务层
│   ├── agentscope_runner.py   # AgentScope 封装
│   ├── procurement_workflow.py # 采购审批工作流
│   ├── storage_service.py     # 存储服务
│   ├── ontology_parser.py     # 本体解析器
│   ├── knowledge_graph.py     # 知识图谱
│   ├── osi_parser.py          # OSI 解析器
│   └── database.py            # 数据库服务
│
├── routes/                    # FastHTML 路由
│   ├── api.py                # REST API
│   └── pages.py              # 页面路由
│
├── configs/                   # 配置文件
│   ├── ontology_procurement.py
│   ├── intents_procurement.py
│   └── skills_procurement.py
│
├── static/                    # 静态资源
│   ├── css/app.css
│   └── js/app.js
│
├── supabase/                  # Supabase 配置
│   ├── config.toml
│   └── migrations/
│
├── tests/                     # 测试
│   └── test_procurement_workflow.py
│
├── .specify/                  # Spec Kit 配置
│   ├── memory/
│   │   └── constitution.md    # 项目规范
│   ├── templates/
│   ├── specs/
│   └── extensions/
│
├── plan.md                    # 迭代面板
└── SPEC.md                    # 本文档
```

---

## 8. 更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-05-18 | 初始化技术文档，创建 Spec Kit 集成 |


---

> 本文档使用 Markdown 格式，每次完成新功能或修改架构后请同步更新。
