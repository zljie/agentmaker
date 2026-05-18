"""
知识图谱服务 - 将本体转换为知识图谱
"""
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class KGNode:
    """知识图谱节点"""
    id: str
    type: str  # entity, action, property, concept
    name: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KGEdge:
    """知识图谱边"""
    source: str
    target: str
    relation: str  # has_property, invokes, applies_to, belongs_to, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


class KnowledgeGraph:
    """知识图谱"""

    def __init__(self, ontology_id: str):
        self.ontology_id = ontology_id
        self.nodes: List[KGNode] = []
        self.edges: List[KGEdge] = []
        self._node_map: Dict[str, KGNode] = {}

    def add_node(self, node: KGNode) -> None:
        """添加节点"""
        self.nodes.append(node)
        self._node_map[node.id] = node

    def add_edge(self, edge: KGEdge) -> None:
        """添加边"""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[KGNode]:
        """获取节点"""
        return self._node_map.get(node_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "ontology_id": self.ontology_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "entity_count": len([n for n in self.nodes if n.type == "entity"]),
                "action_count": len([n for n in self.nodes if n.type == "action"]),
                "property_count": len([n for n in self.nodes if n.type == "property"]),
                "edge_count": len(self.edges),
            }
        }

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def render_for_prompt(self) -> str:
        """渲染为 prompt 格式，供 LLM 使用"""
        lines = ["## 知识图谱上下文"]

        # 实体
        entities = [n for n in self.nodes if n.type == "entity"]
        if entities:
            lines.append("\n### 实体类型:")
            for e in entities:
                props = ", ".join([f"{p['name']}: {p['type']}" for p in e.properties.get("properties", [])]) or "无属性"
                lines.append(f"- **{e.name}** ({e.id})")
                lines.append(f"  - {e.description}")
                lines.append(f"  - 属性: {props}")

        # 操作
        actions = [n for n in self.nodes if n.type == "action"]
        if actions:
            lines.append("\n### 可用操作:")
            for a in actions:
                lines.append(f"- **{a.name}** (`{a.id}`)")
                lines.append(f"  - {a.description}")
                if a.properties.get("input_params"):
                    params = ", ".join(a.properties["input_params"].keys())
                    lines.append(f"  - 输入参数: {params}")

        # 关系
        relations = set(e.relation for e in self.edges)
        if relations:
            lines.append("\n### 关系类型:")
            for rel in relations:
                count = len([e for e in self.edges if e.relation == rel])
                lines.append(f"- `{rel}`: {count} 条")

        return "\n".join(lines)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    @staticmethod
    def from_ontology(ontology) -> KnowledgeGraph:
        """从本体构建知识图谱"""
        kg = KnowledgeGraph(ontology_id=getattr(ontology, 'domain', 'unknown'))

        # 添加实体节点
        for entity in getattr(ontology, 'entities', []):
            node = KGNode(
                id=f"entity:{entity.name}",
                type="entity",
                name=entity.name,
                description=entity.description,
                properties={
                    "properties": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                        }
                        for p in getattr(entity, 'properties', [])
                    ],
                    "labels": getattr(entity, 'labels', []),
                    "dataset": getattr(entity, 'dataset', None),
                },
                labels=getattr(entity, 'labels', []),
            )
            kg.add_node(node)

            # 为实体的每个属性添加节点和边
            for prop in getattr(entity, 'properties', []):
                prop_node = KGNode(
                    id=f"property:{entity.name}.{prop.name}",
                    type="property",
                    name=prop.name,
                    description=prop.description,
                    properties={
                        "data_type": prop.type,
                        "required": prop.required,
                        "default": prop.default,
                    },
                )
                kg.add_node(prop_node)
                kg.add_edge(KGEdge(
                    source=f"entity:{entity.name}",
                    target=f"property:{entity.name}.{prop.name}",
                    relation="has_property",
                ))

        # 添加操作节点
        for action in getattr(ontology, 'actions', []):
            node = KGNode(
                id=f"action:{action.id}",
                type="action",
                name=action.name,
                description=action.description,
                properties={
                    "kind": action.kind,
                    "operation": action.operation,
                    "entity_name": action.entity_name,
                    "input_params": action.input_schema.get("properties", {}) if hasattr(action, 'input_schema') else {},
                    "labels": getattr(action, 'labels', []),
                },
                labels=getattr(action, 'labels', []),
            )
            kg.add_node(node)

            # 操作与实体的关系
            if hasattr(action, 'entity_name') and action.entity_name:
                kg.add_edge(KGEdge(
                    source=f"action:{action.id}",
                    target=f"entity:{action.entity_name}",
                    relation="applies_to",
                ))
            elif hasattr(action, 'applies_to') and action.applies_to:
                kg.add_edge(KGEdge(
                    source=f"action:{action.id}",
                    target=f"entity:{action.applies_to}",
                    relation="applies_to",
                ))

        # 添加规则节点
        for rule in getattr(ontology, 'rules', []):
            node = KGNode(
                id=f"rule:{rule.id}",
                type="rule",
                name=rule.name,
                description=rule.description,
                properties={
                    "condition": rule.condition,
                    "action": rule.action,
                },
            )
            kg.add_node(node)

        return kg


# 全局知识图谱缓存
_kg_cache: Dict[str, KnowledgeGraph] = {}


def get_kg_cache(ontology_id: str) -> Optional[KnowledgeGraph]:
    """获取缓存的知识图谱"""
    return _kg_cache.get(ontology_id)


def set_kg_cache(ontology_id: str, kg: KnowledgeGraph) -> None:
    """设置知识图谱缓存"""
    _kg_cache[ontology_id] = kg


def clear_kg_cache(ontology_id: Optional[str] = None) -> None:
    """清除知识图谱缓存"""
    global _kg_cache
    if ontology_id:
        _kg_cache.pop(ontology_id, None)
    else:
        _kg_cache.clear()
