"""
本体 (Ontology) 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml


@dataclass
class PropertySpec:
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None


@dataclass
class EntitySpec:
    name: str
    description: str
    properties: List[PropertySpec] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    dataset: Optional[str] = None


@dataclass
class ActionSpec:
    id: str
    name: str
    description: str
    kind: str = "query"  # query, operation, analytics
    operation: str = "list"  # list, get, create, update, delete, rank, aggregate
    entity_name: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    applies_to: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    needs_hitl: bool = False


@dataclass
class RuleSpec:
    id: str
    name: str
    description: str
    condition: str
    action: str


@dataclass
class OntologySpec:
    domain: str
    version: str
    description: str = ""
    entities: List[EntitySpec] = field(default_factory=list)
    actions: List[ActionSpec] = field(default_factory=list)
    rules: List[RuleSpec] = field(default_factory=list)
    raw_yaml: str = ""

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "OntologySpec":
        """从 YAML 字符串解析"""
        data = yaml.safe_load(yaml_str)

        entities = []
        for name, ent_data in data.get("entities", {}).items():
            props = [
                PropertySpec(
                    name=p["name"],
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", False),
                )
                for p in ent_data.get("properties", [])
            ]
            entities.append(EntitySpec(
                name=name,
                description=ent_data.get("description", ""),
                properties=props,
                labels=ent_data.get("labels", []),
                dataset=ent_data.get("dataset"),
            ))

        actions = []
        for act_data in data.get("actions", []):
            actions.append(ActionSpec(
                id=act_data["id"],
                name=act_data["name"],
                description=act_data.get("description", ""),
                kind=act_data.get("kind", "query"),
                operation=act_data.get("operation", "list"),
                entity_name=act_data.get("entity_name", ""),
                input_schema=act_data.get("input_schema", {}),
                output_schema=act_data.get("output_schema", {}),
                applies_to=act_data.get("applies_to"),
                labels=act_data.get("labels", []),
                needs_hitl=act_data.get("needs_hitl", False),
            ))

        rules = []
        for rule_data in data.get("rules", []):
            rules.append(RuleSpec(
                id=rule_data["id"],
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                condition=rule_data.get("condition", ""),
                action=rule_data.get("action", ""),
            ))

        return cls(
            domain=data.get("domain", "unknown"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            entities=entities,
            actions=actions,
            rules=rules,
            raw_yaml=yaml_str,
        )

    def to_yaml(self) -> str:
        """序列化为 YAML"""
        data = {
            "domain": self.domain,
            "version": self.version,
            "description": self.description,
            "entities": {},
            "actions": [],
            "rules": [],
        }
        for ent in self.entities:
            data["entities"][ent.name] = {
                "description": ent.description,
                "labels": ent.labels,
                "dataset": ent.dataset,
                "properties": [
                    {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                    for p in ent.properties
                ],
            }
        for act in self.actions:
            data["actions"].append({
                "id": act.id,
                "name": act.name,
                "description": act.description,
                "kind": act.kind,
                "operation": act.operation,
                "entity_name": act.entity_name,
                "input_schema": act.input_schema,
                "output_schema": act.output_schema,
                "applies_to": act.applies_to,
                "labels": act.labels,
                "needs_hitl": act.needs_hitl,
            })
        return yaml.dump(data, allow_unicode=True)

    def render_for_prompt(self) -> str:
        """渲染为本体的 prompt 部分"""
        lines = [f"## 本体: {self.domain} (v{self.version})"]
        lines.append(f"{self.description}\n")

        lines.append("### 实体类型:")
        for ent in self.entities:
            props_str = ", ".join([f"{p.name}: {p.type}" for p in ent.properties]) if ent.properties else "无"
            lines.append(f"- **{ent.name}**: {ent.description}")
            lines.append(f"  - 属性: {props_str}")

        lines.append("\n### 可用操作:")
        for act in self.actions:
            lines.append(f"- `{act.id}`: {act.description}")
            if act.input_schema.get("properties"):
                params = ", ".join(act.input_schema["properties"].keys())
                lines.append(f"  - 参数: {params}")

        return "\n".join(lines)


# 示例本体
SAMPLE_ONTOLOGY = """
domain: procurement
version: 1.0.0
description: 企业采购管理系统本体

entities:
  materials:
    description: 物料主数据
    labels: [master_data]
    dataset: materials
    properties:
      - name: material_id
        type: string
        description: 物料编码
        required: true
      - name: material_name
        type: string
        description: 物料名称
        required: true
      - name: unit
        type: string
        description: 单位

  suppliers:
    description: 供应商主数据
    labels: [master_data]
    dataset: suppliers
    properties:
      - name: supplier_id
        type: string
        description: 供应商编码
        required: true
      - name: supplier_name
        type: string
        description: 供应商名称
        required: true

  purchase_orders:
    description: 采购订单
    labels: [transaction]
    dataset: purchase_orders
    properties:
      - name: po_id
        type: string
        description: 订单编号
        required: true
      - name: supplier_id
        type: string
        description: 供应商

actions:
  - id: materials/list
    name: 查询物料列表
    description: 分页查询物料主数据
    kind: query
    operation: list
    entity_name: materials
    applies_to: materials
    input_schema:
      type: object
      properties:
        plant_id:
          type: string
          description: 工厂编码
        page:
          type: integer
          default: 1
        page_size:
          type: integer
          default: 20

  - id: materials/get_by_id
    name: 获取物料详情
    description: 根据物料编码获取物料详细信息
    kind: query
    operation: get
    entity_name: materials
    applies_to: materials
    input_schema:
      type: object
      required: [material_id]
      properties:
        material_id:
          type: string
          description: 物料编码

  - id: suppliers/list
    name: 查询供应商列表
    description: 分页查询供应商主数据
    kind: query
    operation: list
    entity_name: suppliers
    applies_to: suppliers
    input_schema:
      type: object
      properties:
        page:
          type: integer
          default: 1
        page_size:
          type: integer
          default: 20

  - id: purchase_orders/list
    name: 查询采购订单
    description: 分页查询采购订单
    kind: query
    operation: list
    entity_name: purchase_orders
    applies_to: purchase_orders
    input_schema:
      type: object
      properties:
        supplier_id:
          type: string
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date
        status:
          type: string
        page:
          type: integer
          default: 1
        page_size:
          type: integer
          default: 20

  - id: analytics/top_materials_by_demand
    name: 按需求排名物料
    description: 按指定时间窗口内的需求计划数量汇总排名Top物料
    kind: analytics
    operation: rank
    entity_name: materials
    applies_to: demand_plans
    input_schema:
      type: object
      required: [date_from, date_to]
      properties:
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date
        plant_id:
          type: string
        top_n:
          type: integer
          default: 10
          minimum: 1
          maximum: 100

  - id: analytics/supplier_performance
    name: 供应商绩效分析
    description: 分析供应商的交付绩效
    kind: analytics
    operation: aggregate
    entity_name: suppliers
    applies_to: purchase_orders
    input_schema:
      type: object
      required: [date_from, date_to]
      properties:
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date
        supplier_id:
          type: string
"""
