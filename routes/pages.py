"""
页面路由
"""
from fasthtml.common import *
from markupsafe import Markup

from models.bundle import create_sample_bundle


def page_routes(app: FastHTML):
    """注册页面路由"""

    @app.route("/")
    def home():
        """主页 - 概览"""
        return render_layout(
            title="概览 | NextStudio",
            active_tab="overview",
            content=render_overview(),
        )

    @app.route("/ontology")
    def ontology_page():
        """本体管理"""
        return render_layout(
            title="本体管理 | NextStudio",
            active_tab="ontology",
            content=render_ontology(),
        )

    @app.route("/ontology/{ontology_id}")
    def ontology_detail(ontology_id: str):
        """本体详情"""
        return render_layout(
            title="本体详情 | NextStudio",
            active_tab="ontology",
            content=render_ontology_detail(ontology_id),
        )

    @app.route("/intent")
    def intent_page():
        """意图配置"""
        return render_layout(
            title="意图配置 | NextStudio",
            active_tab="intent",
            content=render_intent(),
        )

    @app.route("/skill")
    def skill_page():
        """技能配置"""
        return render_layout(
            title="技能配置 | NextStudio",
            active_tab="skill",
            content=render_skill(),
        )

    @app.route("/connector")
    def connector_page():
        """连接器管理"""
        return render_layout(
            title="连接器管理 | NextStudio",
            active_tab="connector",
            content=render_connector(),
        )

    @app.route("/agent")
    def agent_page():
        """Agent 构建"""
        return render_layout(
            title="Agent 构建 | NextStudio",
            active_tab="agent",
            content=render_agent(),
        )

    @app.route("/chat")
    def chat_page():
        """对话测试"""
        return render_layout(
            title="对话测试 | NextStudio",
            active_tab="chat",
            content=render_chat(),
        )


def render_layout(title: str, active_tab: str, content: str) -> Table:
    """渲染页面布局"""
    bundle = create_sample_bundle()

    return Html(
        Head(
            Title(title),
            Meta(charset="UTF-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"),
            Style("""
                * { box-sizing: border-box; }
                .tab-content { display: none; }
                .tab-content.active { display: block; }
                .nav-item.active { background-color: #eff6ff; color: #2563eb; border-left: 3px solid #2563eb; font-weight: 500; }
                .card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: box-shadow 0.2s; }
                .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
                .badge { font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 500; display: inline-flex; align-items: center; }
                .badge-blue { background: #dbeafe; color: #1d4ed8; }
                .badge-green { background: #dcfce7; color: #16a34a; }
                .badge-amber { background: #fef3c7; color: #d97706; }
                .badge-purple { background: #f3e8ff; color: #9333ea; }
                .badge-red { background: #fee2e2; color: #dc2626; }
                .badge-slate { background: #f1f5f9; color: #475569; }
                .badge-cyan { background: #ecfeff; color: #0891b2; }
                .pulse-dot { animation: pulse 2s infinite; }
                @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
                .streaming-cursor { animation: blink 1s infinite; color: #3b82f6; }
                @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
                .typewriter-cursor {
                    display: inline-block;
                    color: #3b82f6;
                    font-weight: 400;
                    animation: typewriter-blink 0.8s step-end infinite;
                    margin-left: 1px;
                }
                @keyframes typewriter-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
                .chat-message { animation: fadeIn 0.3s ease-out; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                .message-content h1, .message-content h2, .message-content h3 { margin-top: 1em; margin-bottom: 0.5em; font-weight: 600; }
                .message-content h1 { font-size: 1.25em; }
                .message-content h2 { font-size: 1.1em; }
                .message-content h3 { font-size: 1em; }
                .message-content p { margin: 0.5em 0; }
                .message-content ul, .message-content ol { margin: 0.5em 0; padding-left: 1.5em; }
                .message-content li { margin: 0.25em 0; }
                .message-content table { border-collapse: collapse; margin: 0.5em 0; width: 100%; overflow-x: auto; display: block; }
                .message-content th, .message-content td { border: 1px solid #e2e8f0; padding: 6px 12px; text-align: left; font-size: 0.875em; min-width: 80px; }
                .message-content th { background: #f8fafc; font-weight: 600; }
                .message-content tr:nth-child(even) { background: #f8fafc; }
                .message-content code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.875em; }
                .message-content pre { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 0.5em 0; display: block; }
                .message-content pre code { background: transparent; padding: 0; color: inherit; }
                .message-content blockquote { border-left: 3px solid #94a3b8; padding-left: 12px; margin: 0.5em 0; color: #64748b; }
                .message-content strong { font-weight: 600; }
                .message-content hr { border: none; border-top: 1px solid #e2e8f0; margin: 1em 0; }
                .message-content a { color: #3b82f6; text-decoration: underline; }
                .loading-spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #f3f3f3; border-top: 2px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                .timeline-item { position: relative; padding-left: 30px; border-left: 2px solid #e2e8f0; margin-left: 10px; }
                .timeline-item::before { content: ''; position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6; border: 2px solid white; }
                .toast { position: fixed; bottom: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1001; transform: translateY(100px); opacity: 0; transition: all 0.3s; }
                .toast.show { transform: translateY(0); opacity: 1; }
                .toast-success { background: #10b981; color: white; }
                .toast-error { background: #ef4444; color: white; }
                .toast-info { background: #3b82f6; color: white; }
                .skeleton { background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 6px; }
                @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
                .skeleton-text { height: 12px; margin: 8px 0; }
                .skeleton-title { height: 18px; width: 60%; margin-bottom: 12px; }
                .empty-state { text-align: center; padding: 48px 24px; color: #94a3b8; }
                .empty-state i { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
                .empty-state p { font-size: 14px; }
            """),
        ),
        Body(
            # Header
            Header(
                Div(
                    Div(
                        Div(
                            Div(
                                I(cls="fas fa-brain text-white text-sm"),
                                cls="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center"
                            ),
                            Span("NextStudio", cls="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"),
                            cls="flex items-center gap-2"
                        ),
                        cls="flex items-center"
                    ),
                    Div(
                        A(
                            I(cls="fas fa-stethoscope"),
                            " 测试 LLM",
                            href="#",
                            cls="px-3 py-1.5 border border-slate-200 rounded-full text-xs text-slate-600 hover:bg-slate-50 flex items-center gap-1 transition-colors",
                            onclick="testLlm()"
                        ),
                        A(
                            I(cls="fas fa-comments"),
                            " 对话测试",
                            href="/chat",
                            cls="px-4 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 flex items-center gap-1.5 transition-colors"
                        ),
                        cls="flex items-center gap-2"
                    ),
                    cls="max-w-full mx-auto px-6 py-3 flex items-center justify-between"
                ),
                cls="bg-white border-b sticky top-0 z-50 shadow-sm"
            ),

            # Main Layout
            Div(
                # Sidebar
                Aside(
                    Div(
                        H2("资源配置", cls="text-sm font-semibold text-slate-700 mb-3"),
                        Div(
                            I(cls="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"),
                            Input(
                                placeholder="搜索资源配置...",
                                id="resource-search",
                                cls="w-full pl-8 pr-3 py-2 text-sm border rounded-lg bg-white",
                                oninput="filterResources()"
                            ),
                            cls="relative"
                        ),
                        cls="p-4 border-b bg-slate-50"
                    ),
                    Div(
                        # Overview
                        NavItem("overview", "fa-chart-pie", "概览", "/", is_active=(active_tab == "overview")),
                        # Ontology
                        NavGroup("ontology", "fa-database text-blue-500", "本体管理", [
                            ("ontology-list", "fa-list", "本体列表", "/ontology"),
                            ("ontology-detail", "fa-project-diagram", "本体详情", "/ontology/procurement"),
                        ], is_open=(active_tab.startswith("ontology"))),
                        # Intent
                        NavGroup("intent", "fa-bullseye text-purple-500", "意图配置", [
                            ("intent-list", "fa-list", "意图列表", "/intent"),
                        ], is_open=(active_tab == "intent")),
                        # Skill
                        NavGroup("skill", "fa-tools text-amber-500", "技能配置", [
                            ("skill-list", "fa-list", "技能列表", "/skill"),
                        ], is_open=(active_tab == "skill")),
                        # Connector
                        NavGroup("connector", "fa-link text-cyan-500", "连接器", [
                            ("connector-list", "fa-server", "连接器列表", "/connector"),
                        ], is_open=(active_tab == "connector")),
                        # Agent
                        NavItem("agent", "fa-robot text-indigo-500", "Agent 构建", "/agent", is_active=(active_tab == "agent")),
                        # Chat
                        NavItem("chat", "fa-comments text-green-500", "对话测试", "/chat", is_active=(active_tab == "chat")),
                        cls="flex-1 overflow-y-auto p-3 space-y-1"
                    ),
                    cls="w-72 bg-white border-r flex flex-col overflow-hidden"
                ),

                # Main Content
                Main(
                    # Tab Header
                    Div(
                        H2(title.split("|")[0].strip(), cls="text-lg font-semibold text-slate-800", id="tab-title"),
                        Div(id="tab-actions", cls="flex items-center gap-2"),
                        cls="bg-white border-b px-6 py-3 flex items-center justify-between"
                    ),
                    # Content
                    Div(
                        MainContent(active_tab, content),
                        cls="flex-1 overflow-y-auto p-6"
                    ),
                    cls="flex-1 flex flex-col overflow-hidden"
                ),
                cls="flex",
                style="height: calc(100vh - 56px);"
            ),

            # Toast Container
            Div(id="toast-container"),

            # JS
            Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
            Script(src="/static/js/app.js"),

            cls="bg-slate-100 text-slate-800"
        )
    )


def NavItem(id: str, icon: str, label: str, href: str, is_active: bool = False) -> Div:
    """导航项"""
    return A(
        I(cls=f"{icon} w-5"),
        Span(label, cls="flex-1 text-left"),
        href=href,
        cls=f"resource-item w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-600 hover:bg-blue-50 rounded-lg{' active' if is_active else ''}",
        data_resource=id
    )


def NavGroup(group_id: str, icon: str, label: str, items: list, is_open: bool = False) -> Div:
    """导航组"""
    return Div(
        Button(
            I(cls=f"{icon} w-5"),
            Span(label, cls="flex-1 text-left"),
            I(cls="fas fa-chevron-down text-xs text-slate-400 transition-transform duration-200", id=f"chevron-{group_id}"),
            cls="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 rounded-lg",
            onclick=f"toggleGroup('{group_id}')"
        ),
        Div(
            *[A(
                I(cls=f"{icon_cls} w-4"),
                Span(item_label, cls="flex-1 text-left"),
                href=item_href,
                cls="resource-item w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-600 hover:bg-blue-50 rounded-lg ml-7",
                data_resource=item_id
            ) for item_id, icon_cls, item_label, item_href in items],
            id=f"group-{group_id}",
            cls="space-y-1 mt-1",
            style=f"display: {'block' if is_open else 'none'};"
        ),
        cls="resource-group",
        data_group=group_id
    )


def MainContent(active_tab: str, content: str) -> Div:
    """主内容区"""
    return Div(
        Div(Markup(content), id=f"tab-{active_tab}", cls="tab-content active"),
        cls="flex-col gap-6 flex"
    )


def render_overview() -> str:
    """概览页"""
    bundle = create_sample_bundle()
    ontology = bundle.ontology

    return f"""
    <div class="grid grid-cols-5 gap-4">
        <div class="card p-4 cursor-pointer" onclick="location.href='/ontology'">
            <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center mb-3">
                <i class="fas fa-database text-blue-600"></i>
            </div>
            <div class="text-2xl font-bold text-slate-800">{len(ontology.entities)}</div>
            <div class="text-xs text-slate-500">本体模型</div>
        </div>
        <div class="card p-4 cursor-pointer" onclick="location.href='/intent'">
            <div class="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center mb-3">
                <i class="fas fa-bullseye text-purple-600"></i>
            </div>
            <div class="text-2xl font-bold text-slate-800">{len(bundle.intents)}</div>
            <div class="text-xs text-slate-500">意图定义</div>
        </div>
        <div class="card p-4 cursor-pointer" onclick="location.href='/skill'">
            <div class="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center mb-3">
                <i class="fas fa-tools text-amber-600"></i>
            </div>
            <div class="text-2xl font-bold text-slate-800">{len(bundle.skills)}</div>
            <div class="text-xs text-slate-500">Skills</div>
        </div>
        <div class="card p-4 cursor-pointer" onclick="location.href='/connector'">
            <div class="w-10 h-10 rounded-lg bg-cyan-100 flex items-center justify-center mb-3">
                <i class="fas fa-link text-cyan-600"></i>
            </div>
            <div class="text-2xl font-bold text-slate-800">{len(bundle.connector_registry.list_all())}</div>
            <div class="text-xs text-slate-500">连接器</div>
        </div>
        <div class="card p-4 cursor-pointer" onclick="location.href='/agent'">
            <div class="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center mb-3">
                <i class="fas fa-robot text-indigo-600"></i>
            </div>
            <div class="text-2xl font-bold text-slate-800">1</div>
            <div class="text-xs text-slate-500">Agents</div>
        </div>
    </div>

    <div class="card p-6">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">平台资源架构</h3>
        <div class="flex items-center justify-center">
            <div class="flex flex-col items-center gap-4">
                <div class="flex gap-3">
                    <div class="text-center">
                        <div class="w-14 h-14 rounded-xl bg-blue-100 border-2 border-blue-300 flex items-center justify-center mb-2">
                            <i class="fas fa-database text-blue-600 text-lg"></i>
                        </div>
                        <div class="text-xs font-medium">{len(ontology.entities)} 实体</div>
                    </div>
                    <div class="text-center">
                        <div class="w-14 h-14 rounded-xl bg-purple-100 border-2 border-purple-300 flex items-center justify-center mb-2">
                            <i class="fas fa-bullseye text-purple-600 text-lg"></i>
                        </div>
                        <div class="text-xs font-medium">{len(ontology.actions)} 操作</div>
                    </div>
                    <div class="text-center">
                        <div class="w-14 h-14 rounded-xl bg-amber-100 border-2 border-amber-300 flex items-center justify-center mb-2">
                            <i class="fas fa-tools text-amber-600 text-lg"></i>
                        </div>
                        <div class="text-xs font-medium">{len(bundle.skills)} 技能</div>
                    </div>
                    <div class="text-center">
                        <div class="w-14 h-14 rounded-xl bg-cyan-100 border-2 border-cyan-300 flex items-center justify-center mb-2">
                            <i class="fas fa-link text-cyan-600 text-lg"></i>
                        </div>
                        <div class="text-xs font-medium">{len(bundle.connector_registry.list_all())} 连接器</div>
                    </div>
                    <div class="text-center">
                        <div class="w-14 h-14 rounded-xl bg-indigo-100 border-2 border-indigo-300 flex items-center justify-center mb-2">
                            <i class="fas fa-robot text-indigo-600 text-lg"></i>
                        </div>
                        <div class="text-xs font-medium">1 Agent</div>
                    </div>
                </div>
                <div class="text-slate-400"><i class="fas fa-arrow-down text-2xl"></i></div>
                <div class="px-8 py-4 bg-indigo-50 border-2 border-indigo-300 rounded-xl text-center">
                    <div class="text-sm font-semibold text-indigo-700 mb-1">AgentScope Runtime</div>
                    <div class="text-xs text-indigo-600">{len(bundle.intents)} 意图 · {len(bundle.skills)} 技能</div>
                </div>
            </div>
        </div>
    </div>

    <div class="card p-6">
        <h3 class="text-sm font-semibold text-slate-700 mb-4">快速开始</h3>
        <div class="grid grid-cols-3 gap-4">
            <a href="/chat" class="p-4 border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-blue-300 transition-all">
                <div class="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center mb-3">
                    <i class="fas fa-comments text-green-600"></i>
                </div>
                <div class="font-medium text-slate-800">对话测试</div>
                <div class="text-xs text-slate-500 mt-1">开始与 Agent 对话</div>
            </a>
            <a href="/agent" class="p-4 border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-indigo-300 transition-all">
                <div class="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center mb-3">
                    <i class="fas fa-magic text-indigo-600"></i>
                </div>
                <div class="font-medium text-slate-800">Agent 构建</div>
                <div class="text-xs text-slate-500 mt-1">配置新的 Agent</div>
            </a>
            <a href="/connector" class="p-4 border border-slate-200 rounded-lg hover:bg-slate-50 hover:border-cyan-300 transition-all">
                <div class="w-10 h-10 rounded-lg bg-cyan-100 flex items-center justify-center mb-3">
                    <i class="fas fa-plug text-cyan-600"></i>
                </div>
                <div class="font-medium text-slate-800">连接器配置</div>
                <div class="text-xs text-slate-500 mt-1">管理 API 连接</div>
            </a>
        </div>
    </div>
    """


def render_ontology() -> str:
    """本体管理页"""
    bundle = create_sample_bundle()
    ont = bundle.ontology
    return f"""
    <div class="card p-6">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">本体列表</h3>
            <div class="flex gap-2">
                <button onclick="loadOntologyRaw()" class="px-3 py-1.5 text-xs border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                    <i class="fas fa-code mr-1"></i>查看 YAML
                </button>
            </div>
        </div>
        <div class="space-y-3" id="ontology-list">
            <div class="p-4 border border-slate-200 rounded-lg border-l-4 border-l-blue-500">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-slate-800">{ont.domain}</div>
                        <div class="text-xs text-slate-500 mt-1">{ont.description}</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="badge badge-blue">v{ont.version}</span>
                        <span class="text-xs text-slate-400">{len(ont.entities)} 实体, {len(ont.actions)} 操作</span>
                    </div>
                </div>
                <div class="mt-3 flex flex-wrap gap-1.5">
                    <span class="badge badge-slate"><i class="fas fa-cube mr-1"></i>{len(ont.entities)} 实体类型</span>
                    <span class="badge badge-slate"><i class="fas fa-bolt mr-1"></i>{len(ont.actions)} 操作</span>
                    <span class="badge badge-slate"><i class="fas fa-gavel mr-1"></i>{len(ont.rules)} 规则</span>
                </div>
            </div>
        </div>
    </div>

    <div id="ontology-raw-modal" class="hidden fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4">
        <div class="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div class="flex items-center justify-between p-4 border-b sticky top-0 bg-white z-10">
                <h3 class="font-semibold text-slate-800">本体 YAML</h3>
                <button onclick="closeOntologyRawModal()" class="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors">✕</button>
            </div>
            <div class="p-4">
                <pre id="ontology-yaml-content" class="bg-slate-900 text-slate-100 p-4 rounded-lg text-xs overflow-x-auto leading-relaxed" style="max-height: 60vh; white-space: pre-wrap; word-break: break-all;"></pre>
            </div>
        </div>
    </div>
    """


def render_ontology_detail(ontology_id: str) -> str:
    """本体详情页"""
    bundle = create_sample_bundle()
    ont = bundle.ontology

    entity_cards = "".join(
        f'''
        <div class="p-4 border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all">
            <div class="flex items-center justify-between mb-2">
                <div class="font-medium font-mono text-slate-800 text-sm">{e.name}</div>
                <span class="badge badge-blue">实体</span>
            </div>
            <div class="text-xs text-slate-500 mb-3">{e.description}</div>
            <div class="flex flex-wrap gap-1">
                {"".join(f'<span class="badge badge-slate">{l}</span>' for l in e.labels)}
            </div>
            {f'<div class="mt-3 pt-3 border-t border-slate-100"><div class="text-xs text-slate-400 mb-1">属性</div>' + "".join(f'<span class="text-xs font-mono text-slate-600 bg-slate-50 px-2 py-0.5 rounded mr-1">{p.name}: <span class="text-slate-400">{p.type}</span></span>' for p in e.properties) + '</div>' if e.properties else ''}
        </div>'''
        for e in ont.entities
    )

    action_cards = "".join(
        f'''
        <div class="p-4 border border-slate-200 rounded-lg hover:border-purple-300 hover:shadow-sm transition-all">
            <div class="flex items-center justify-between mb-2">
                <div class="font-mono text-xs text-purple-600">{a.id}</div>
                <span class="badge badge-purple">{a.kind}</span>
            </div>
            <div class="text-sm text-slate-700 mb-2">{a.name}</div>
            <div class="text-xs text-slate-500 mb-2">{a.description}</div>
            <div class="flex flex-wrap gap-1">
                {"".join(f'<span class="badge badge-slate">{l}</span>' for l in a.labels)}
            </div>
        </div>'''
        for a in ont.actions
    )

    return f"""
    <div class="grid grid-cols-2 gap-6">
        <div class="card p-6">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <i class="fas fa-cube text-blue-500"></i> 实体类型
                <span class="badge badge-slate ml-auto">{len(ont.entities)}</span>
            </h3>
            <div class="space-y-3">
                {entity_cards if entity_cards else '<div class="empty-state"><i class="fas fa-database"></i><p>暂无实体</p></div>'}
            </div>
        </div>
        <div class="card p-6">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <i class="fas fa-bolt text-purple-500"></i> 可用操作
                <span class="badge badge-slate ml-auto">{len(ont.actions)}</span>
            </h3>
            <div class="space-y-3">
                {action_cards if action_cards else '<div class="empty-state"><i class="fas fa-bolt"></i><p>暂无操作</p></div>'}
            </div>
        </div>
    </div>
    """


def render_intent() -> str:
    """意图配置页"""
    bundle = create_sample_bundle()
    intent_rows = "".join(
        f'''
        <div class="p-4 border border-slate-200 rounded-lg border-l-4 border-l-purple-500 hover:border-purple-300 hover:shadow-sm transition-all">
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-medium text-slate-800">{i.type}</div>
                    <div class="text-xs text-slate-500 mt-1">{i.description}</div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge badge-purple">{i.priority} 分</span>
                    <span class="badge badge-{'green' if i.enabled else 'red'}">{i.enabled and "已启用" or "已禁用"}</span>
                </div>
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
                {("".join(f'<span class="badge badge-slate">{kw}</span>' for kw in i.keywords)) if i.keywords else '<span class="text-xs text-slate-400">无关键词</span>'}
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
                {("".join(f'<span class="font-mono text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">{a}</span>' for a in i.actions)) if i.actions else '<span class="text-xs text-slate-400">无关联操作</span>'}
            </div>
        </div>'''
        for i in bundle.intents
    )
    return f"""
    <div class="card p-6">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">意图列表</h3>
            <button class="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                <i class="fas fa-plus mr-1"></i>新建意图
            </button>
        </div>
        <div class="space-y-3" id="intent-list">
            {intent_rows if intent_rows else '<div class="empty-state"><i class="fas fa-bullseye"></i><p>暂无意图定义</p></div>'}
        </div>
    </div>
    """


def render_skill() -> str:
    """技能配置页"""
    bundle = create_sample_bundle()
    skill_cards = "".join(
        f'''
        <div class="p-4 border border-slate-200 rounded-lg border-l-4 border-l-amber-500 hover:border-amber-300 hover:shadow-sm transition-all">
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-medium text-slate-800">{s.name}</div>
                    <div class="text-xs text-slate-500 mt-1">{s.description}</div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge badge-{'green' if s.enabled else 'red'}">{s.enabled and "已启用" or "已禁用"}</span>
                    <span class="badge badge-amber">{s.priority} 分</span>
                </div>
            </div>
            <div class="mt-2 text-xs text-slate-400 font-mono">
                <i class="fas fa-bolt mr-1"></i>{s.action_id}
                <span class="ml-2 badge badge-slate">{s.kind}</span>
            </div>
        </div>'''
        for s in bundle.skills
    )
    return f"""
    <div class="card p-6">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">技能列表</h3>
        </div>
        <div class="grid grid-cols-2 gap-4" id="skill-list">
            {skill_cards if skill_cards else '<div class="empty-state"><i class="fas fa-tools"></i><p>暂无技能</p></div>'}
        </div>
    </div>
    """


def render_connector() -> str:
    """连接器管理页"""
    bundle = create_sample_bundle()
    connectors = bundle.connector_registry.list_all()

    connector_cards = "".join(
        f'''
        <div class="p-4 border border-slate-200 rounded-lg border-l-4 border-l-cyan-500 hover:border-cyan-300 hover:shadow-sm transition-all">
            <div class="flex items-center justify-between">
                <div>
                    <div class="font-medium text-slate-800">{c.name}</div>
                    <div class="text-xs text-slate-500 mt-1">{c.description}</div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge badge-cyan">{'Mock' if c.is_mock else 'Real'}</span>
                    <span class="badge badge-slate">{len(c.actions)} Actions</span>
                    <span class="badge badge-{'green' if c.enabled else 'red'}">{c.enabled and "已启用" or "已禁用"}</span>
                </div>
            </div>
            <div class="mt-3 grid grid-cols-3 gap-2">
                {("".join(f'<div class="p-2 bg-slate-50 rounded text-xs font-mono text-slate-600 truncate" title="{a.id}">{a.id}</div>' for a in c.actions)) if c.actions else '<div class="text-xs text-slate-400">无 Action</div>'}
            </div>
        </div>'''
        for c in connectors
    )
    return f"""
    <div class="card p-6">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">连接器列表</h3>
        </div>
        <div class="space-y-4" id="connector-list">
            {connector_cards if connector_cards else '<div class="empty-state"><i class="fas fa-server"></i><p>暂无连接器</p></div>'}
        </div>
    </div>
    """


def render_agent() -> str:
    """Agent 构建页"""
    bundle = create_sample_bundle()

    intent_badge = "".join(
        f'<span class="badge badge-purple">{i.type}</span>'
        for i in bundle.intents
    )
    skill_badge = "".join(
        f'<span class="badge badge-amber">{s.name}</span>'
        for s in bundle.skills
    )
    connector_badge = "".join(
        f'<span class="badge badge-cyan">{c.name}</span>'
        for c in bundle.connector_registry.list_all()
    )

    return f"""
    <div class="grid grid-cols-3 gap-6">
        <div class="col-span-2 card p-6">
            <h3 class="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <i class="fas fa-robot text-indigo-500"></i> 当前 Agent 配置
            </h3>
            <div class="grid grid-cols-2 gap-6">
                <div>
                    <div class="text-xs text-slate-400 mb-1">Agent 名称</div>
                    <div class="font-medium text-slate-800">{bundle.agent_config.name}</div>
                </div>
                <div>
                    <div class="text-xs text-slate-400 mb-1">描述</div>
                    <div class="text-slate-800">{bundle.agent_config.description}</div>
                </div>
                <div>
                    <div class="text-xs text-slate-400 mb-1">版本</div>
                    <div class="font-medium text-slate-800">{bundle.agent_config.version}</div>
                </div>
                <div>
                    <div class="text-xs text-slate-400 mb-1">最大迭代次数</div>
                    <div class="font-medium text-slate-800">{bundle.runtime.max_iters}</div>
                </div>
            </div>

            <div class="mt-6 flex gap-3">
                <a href="/chat" class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors">
                    <i class="fas fa-play mr-2"></i>测试运行
                </a>
                <button class="px-4 py-2 border border-slate-200 text-slate-600 text-sm rounded-lg hover:bg-slate-50 transition-colors">
                    <i class="fas fa-download mr-2"></i>导出配置
                </button>
            </div>
        </div>

        <div class="space-y-4">
            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3">
                    <i class="fas fa-database mr-1"></i>本体
                </h3>
                <div class="flex flex-wrap gap-1">
                    <span class="badge badge-blue">{bundle.ontology.domain} v{bundle.ontology.version}</span>
                </div>
            </div>
            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3">
                    <i class="fas fa-bullseye mr-1"></i>意图 ({len(bundle.intents)})
                </h3>
                <div class="flex flex-wrap gap-1">
                    {intent_badge if intent_badge else '<span class="text-xs text-slate-400">暂无</span>'}
                </div>
            </div>
            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3">
                    <i class="fas fa-tools mr-1"></i>技能 ({len(bundle.skills)})
                </h3>
                <div class="flex flex-wrap gap-1">
                    {skill_badge if skill_badge else '<span class="text-xs text-slate-400">暂无</span>'}
                </div>
            </div>
            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3">
                    <i class="fas fa-link mr-1"></i>连接器 ({len(bundle.connector_registry.list_all())})
                </h3>
                <div class="flex flex-wrap gap-1">
                    {connector_badge if connector_badge else '<span class="text-xs text-slate-400">暂无</span>'}
                </div>
            </div>
        </div>
    </div>
    """


def render_chat() -> str:
    """对话测试页"""
    bundle = create_sample_bundle()
    return f"""
    <div class="grid grid-cols-3 gap-6 h-full" style="height: calc(100vh - 120px);">
        <!-- Chat Area -->
        <div class="col-span-2 card flex flex-col overflow-hidden" style="height: 100%;">
            <!-- Header -->
            <div class="px-4 py-3 border-b bg-slate-50 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                        <i class="fas fa-robot text-blue-600 text-sm"></i>
                    </div>
                    <div>
                        <div class="font-semibold text-sm text-slate-800">{bundle.agent_config.name}</div>
                        <div class="text-xs text-slate-400">{bundle.agent_config.description}</div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span class="text-xs text-slate-400">在线</span>
                </div>
            </div>

            <!-- Messages -->
            <div class="flex-1 overflow-y-auto p-4 space-y-3" id="chat-messages">
            </div>

            <!-- Execution Timeline -->
            <div class="border-t px-4 py-3 bg-slate-50 hidden" id="execution-timeline">
                <div class="flex items-center gap-2 mb-2">
                    <i class="fas fa-stream text-xs text-slate-400"></i>
                    <span class="text-xs font-semibold text-slate-600">执行过程</span>
                </div>
                <div id="timeline-content" class="space-y-1 max-h-32 overflow-y-auto"></div>
            </div>

            <!-- Thinking Indicator -->
            <div class="border-t px-4 py-3 bg-slate-50 hidden flex items-center gap-2" id="thinking-indicator">
                <div class="flex gap-1">
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 0ms;"></span>
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 150ms;"></span>
                    <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style="animation-delay: 300ms;"></span>
                </div>
                <span id="thinking-text" class="text-xs text-slate-500">正在理解您的问题...</span>
            </div>

            <!-- Input Area -->
            <div class="p-4 border-t">
                <div class="flex gap-3">
                    <input
                        type="text"
                        id="chat-input"
                        placeholder="输入您的问题，按 Enter 发送..."
                        class="flex-1 px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        onkeydown="if(event.key==='Enter') sendMessage()"
                    >
                    <button
                        id="send-btn"
                        onclick="sendMessage()"
                        class="px-5 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors flex items-center gap-2"
                    >
                        <i class="fas fa-paper-plane text-sm"></i>
                    </button>
                    <button
                        id="abort-btn"
                        onclick="abortMessage()"
                        class="px-5 py-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors hidden flex items-center gap-2"
                    >
                        <i class="fas fa-stop text-sm"></i>
                    </button>
                </div>
                <div class="mt-2 flex items-center justify-between text-xs text-slate-400">
                    <span><i class="fas fa-shield-halved mr-1"></i>使用 Mock Connector (无需 API Key)</span>
                    <label class="flex items-center gap-1.5 cursor-pointer">
                        <input type="checkbox" id="use-mock" checked class="rounded text-blue-600">
                        <span>Mock 模式</span>
                    </label>
                </div>
            </div>
        </div>

        <!-- Side Panel -->
        <div class="space-y-4 overflow-y-auto">
            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wide">当前配置</h3>
                <div class="space-y-2 text-xs">
                    <div class="flex justify-between py-1 border-b border-slate-100">
                        <span class="text-slate-400">本体</span>
                        <span class="text-slate-700 font-medium">{bundle.ontology.domain}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-100">
                        <span class="text-slate-400">版本</span>
                        <span class="text-slate-700">{bundle.ontology.version}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-100">
                        <span class="text-slate-400">意图</span>
                        <span class="text-slate-700">{len(bundle.intents)} 个</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-100">
                        <span class="text-slate-400">技能</span>
                        <span class="text-slate-700">{len(bundle.skills)} 个</span>
                    </div>
                    <div class="flex justify-between py-1">
                        <span class="text-slate-400">连接器</span>
                        <span class="text-slate-700">{next((c.name for c in bundle.connector_registry.list_all()), '—')}</span>
                    </div>
                </div>
            </div>

            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wide">示例问题</h3>
                <div class="space-y-1.5">
                    <button onclick="sendExample('查询所有物料')" class="w-full text-left px-3 py-2 text-xs bg-slate-50 rounded-lg hover:bg-blue-50 hover:text-blue-600 transition-colors">
                        <i class="fas fa-database text-blue-400 mr-2 w-4"></i>查询所有物料
                    </button>
                    <button onclick="sendExample('有哪些供应商？')" class="w-full text-left px-3 py-2 text-xs bg-slate-50 rounded-lg hover:bg-green-50 hover:text-green-600 transition-colors">
                        <i class="fas fa-building text-green-400 mr-2 w-4"></i>有哪些供应商？
                    </button>
                    <button onclick="sendExample('查看最近的采购订单')" class="w-full text-left px-3 py-2 text-xs bg-slate-50 rounded-lg hover:bg-amber-50 hover:text-amber-600 transition-colors">
                        <i class="fas fa-file-alt text-amber-400 mr-2 w-4"></i>查看最近的采购订单
                    </button>
                    <button onclick="sendExample('需求量最大的物料是什么？')" class="w-full text-left px-3 py-2 text-xs bg-slate-50 rounded-lg hover:bg-purple-50 hover:text-purple-600 transition-colors">
                        <i class="fas fa-chart-bar text-purple-400 mr-2 w-4"></i>需求量最大的物料是什么？
                    </button>
                </div>
            </div>

            <div class="card p-4">
                <h3 class="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wide">快捷操作</h3>
                <div class="space-y-1.5">
                    <button onclick="clearChat()" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                        <i class="fas fa-trash mr-2 text-slate-400"></i>清空对话
                    </button>
                    <button onclick="exportChat()" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                        <i class="fas fa-download mr-2 text-slate-400"></i>导出对话
                    </button>
                </div>
            </div>
        </div>
    </div>
    """
