"""
Bundle (运行时配置包) 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
from .ontology import OntologySpec, SAMPLE_ONTOLOGY
from .intent import IntentSpec, SAMPLE_INTENTS, IntentRouter, IntentClassification
from .skill import SkillSpec, SkillRegistry
from .connector import ConnectorConfig, ConnectorRegistry


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str = "采购助手"
    description: str = "企业采购管理助手"
    version: str = "1.0.0"
    system_prompt: str = ""


@dataclass
class RuntimeConfig:
    """运行时配置"""
    max_iters: int = 10
    temperature: float = 0.7
    stream: bool = True
    show_thinking: bool = True


@dataclass
class Bundle:
    """
    Bundle 是运行时的唯一输入配置包
    包含: 本体、意图、技能、连接器、策略、Agent配置、运行时配置
    """
    ontology: OntologySpec
    intents: List[IntentSpec] = field(default_factory=list)
    skills: List[SkillSpec] = field(default_factory=list)
    connectors: List[ConnectorConfig] = field(default_factory=list)
    agent_config: AgentConfig = field(default_factory=AgentConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    policies: Dict[str, Any] = field(default_factory=dict)

    # 运行时实例
    intent_router: Optional[IntentRouter] = None
    skill_registry: Optional[SkillRegistry] = None
    connector_registry: Optional[ConnectorRegistry] = None

    def initialize(self):
        """初始化运行时组件"""
        self.intent_router = IntentRouter(self.intents)
        self.skill_registry = SkillRegistry()
        for skill in self.skills:
            self.skill_registry.register(skill)
        self.connector_registry = ConnectorRegistry()
        for conn in self.connectors:
            self.connector_registry.register(conn)

    def build_system_prompt(self) -> str:
        """构建 System Prompt"""
        parts = [
            f"# {self.agent_config.name} - {self.agent_config.description}",
            "",
            "## 角色定义",
            "你是一个专业的企业采购管理助手，帮助用户查询物料、供应商、采购订单等数据，并进行分析。",
            "",
            self.ontology.render_for_prompt(),
            "",
        ]

        if self.skills:
            parts.append(self.skill_registry.render_for_prompt())

        parts.extend([
            "",
            "## 行为准则",
            "1. 始终使用中文回复",
            "2. 回答简洁明了，数据准确",
            "3. 如需执行操作，使用提供的工具",
            "4. 如果不确定参数，主动询问用户",
            "",
            "## 输出格式",
            "- 查询结果请用表格展示",
            "- 分析结果请用图表说明",
            "- 重要信息请加粗标注",
        ])

        return "\n".join(parts)

    def classify_intent(self, message: str) -> IntentClassification:
        """对消息进行意图分类"""
        if not self.intent_router:
            self.initialize()
        return self.intent_router.classify(message)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "ontology": {
                "domain": self.ontology.domain,
                "version": self.ontology.version,
                "description": self.ontology.description,
                "entities": [
                    {"name": e.name, "description": e.description, "labels": e.labels}
                    for e in self.ontology.entities
                ],
                "actions": [
                    {"id": a.id, "name": a.name, "description": a.description, "kind": a.kind}
                    for a in self.ontology.actions
                ],
            },
            "intents": [
                {"type": i.type, "name": i.name, "actions": i.actions}
                for i in self.intents
            ],
            "skills": [
                {"id": s.id, "name": s.name, "action_id": s.action_id}
                for s in self.skills
            ],
            "agent_config": {
                "name": self.agent_config.name,
                "description": self.agent_config.description,
            },
            "runtime": {
                "max_iters": self.runtime.max_iters,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bundle":
        """从字典创建 Bundle"""
        ontology_data = data.get("ontology", {})
        ontology = OntologySpec(
            domain=ontology_data.get("domain", "unknown"),
            version=ontology_data.get("version", "1.0.0"),
            description=ontology_data.get("description", ""),
        )

        intents_data = data.get("intents", [])
        intents = [
            IntentSpec(
                type=i.get("type", ""),
                name=i.get("name", ""),
                description=i.get("description", ""),
                actions=i.get("actions", []),
            )
            for i in intents_data
        ]

        skills_data = data.get("skills", [])
        skills = [
            SkillSpec(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                action_id=s.get("action_id", ""),
            )
            for s in skills_data
        ]

        agent_config_data = data.get("agent_config", {})
        agent_config = AgentConfig(
            name=agent_config_data.get("name", "采购助手"),
            description=agent_config_data.get("description", ""),
        )

        runtime_data = data.get("runtime", {})
        runtime = RuntimeConfig(
            max_iters=runtime_data.get("max_iters", 10),
        )

        bundle = cls(
            ontology=ontology,
            intents=intents,
            skills=skills,
            agent_config=agent_config,
            runtime=runtime,
        )
        bundle.initialize()
        return bundle


def create_sample_bundle() -> Bundle:
    """创建示例 Bundle"""
    ontology = OntologySpec.from_yaml(SAMPLE_ONTOLOGY)
    intents = IntentSpec.from_yaml(SAMPLE_INTENTS)

    skills = [
        SkillSpec(
            id="skill/materials_query",
            name="物料查询技能",
            description="查询物料主数据，支持分页筛选",
            action_id="materials/list",
            tool="materials_list",
            kind="query",
            operation="list",
            entity_name="materials",
            labels=["query", "materials"],
            enabled=True,
            priority=50,
        ),
        SkillSpec(
            id="skill/suppliers_query",
            name="供应商查询技能",
            description="查询供应商主数据",
            action_id="suppliers/list",
            tool="suppliers_list",
            kind="query",
            operation="list",
            entity_name="suppliers",
            labels=["query", "suppliers"],
            enabled=True,
            priority=50,
        ),
        SkillSpec(
            id="skill/orders_query",
            name="采购订单查询技能",
            description="查询采购订单，支持按供应商、日期筛选",
            action_id="purchase_orders/list",
            tool="orders_list",
            kind="query",
            operation="list",
            entity_name="purchase_orders",
            labels=["query", "orders"],
            enabled=True,
            priority=50,
        ),
        SkillSpec(
            id="skill/demand_analytics",
            name="需求分析技能",
            description="按需求计划数量排名Top物料",
            action_id="analytics/top_materials_by_demand",
            tool="top_materials",
            kind="analytics",
            operation="rank",
            entity_name="materials",
            labels=["analytics", "demand"],
            enabled=True,
            priority=40,
        ),
        SkillSpec(
            id="skill/supplier_perf_analytics",
            name="供应商绩效分析",
            description="分析供应商交付绩效",
            action_id="analytics/supplier_performance",
            tool="supplier_perf",
            kind="analytics",
            operation="aggregate",
            entity_name="suppliers",
            labels=["analytics", "supplier"],
            enabled=True,
            priority=40,
        ),
    ]

    bundle = Bundle(
        ontology=ontology,
        intents=intents,
        skills=skills,
    )
    bundle.initialize()
    return bundle
