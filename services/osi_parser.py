"""
OSI (Open Semantic Interface) 格式解析器
用于解析来自 GitHub OSI Model Generator 的本体文件
参考: https://github.com/zljie/osi-model-generator-skill
"""
import yaml
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class OSIFieldSpec:
    """OSI 字段定义"""
    name: str
    type: str
    description: str = ""
    expression: str = ""
    dimension: Optional[Dict] = None


@dataclass
class OSIDatasetSpec:
    """OSI 数据集定义 (对应实体)"""
    name: str
    source: str
    description: str
    primary_key: List[str] = field(default_factory=list)
    fields: List[OSIFieldSpec] = field(default_factory=list)


@dataclass
class OSIRelationshipSpec:
    """OSI 关系定义"""
    name: str
    from_entity: str
    to_entity: str
    from_columns: List[str] = field(default_factory=list)
    to_columns: List[str] = field(default_factory=list)


@dataclass
class OSIMetricSpec:
    """OSI 指标定义"""
    name: str
    expression: str
    description: str = ""


@dataclass
class OSIActionSpec:
    """OSI Action 定义"""
    id: str
    name: str
    kind: str = "query"
    operation: str = "list"
    entity_name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)


@dataclass
class OSIRuleSpec:
    """OSI 规则定义"""
    id: str
    name: str
    description: str = ""
    severity: str = "info"
    message: str = ""


@dataclass
class OSISemanticModel:
    """OSI 语义模型"""
    name: str
    description: str
    instructions: str = ""
    synonyms: List[str] = field(default_factory=list)
    datasets: List[OSIDatasetSpec] = field(default_factory=list)
    relationships: List[OSIRelationshipSpec] = field(default_factory=list)
    metrics: List[OSIMetricSpec] = field(default_factory=list)
    actions: List[OSIActionSpec] = field(default_factory=list)
    rules: List[OSIRuleSpec] = field(default_factory=list)


def is_osi_format(content: str) -> bool:
    """检测是否为 OSI 格式"""
    try:
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            # OSI 格式的特征: 有 version 和 semantic_model 字段
            return "version" in data and "semantic_model" in data
        return False
    except:
        return False


def parse_osi_yaml(yaml_str: str) -> OSISemanticModel:
    """解析 OSI 格式的 YAML"""
    data = yaml.safe_load(yaml_str)

    # 获取第一个语义模型
    semantic_models = data.get("semantic_model", [])
    if not semantic_models:
        raise ValueError("No semantic_model found in YAML")

    model_data = semantic_models[0] if isinstance(semantic_models, list) else semantic_models

    # 解析数据集
    datasets = []
    for ds in model_data.get("datasets", []):
        fields = []
        for f in ds.get("fields", []):
            fields.append(OSIFieldSpec(
                name=f.get("name", ""),
                type=f.get("type", "String"),
                description=f.get("description", ""),
                expression=f.get("expression", {}).get("dialects", [{}])[0].get("expression", "") if f.get("expression") else "",
                dimension=f.get("dimension"),
            ))
        datasets.append(OSIDatasetSpec(
            name=ds.get("name", ""),
            source=ds.get("source", ""),
            description=ds.get("description", ""),
            primary_key=ds.get("primary_key", []),
            fields=fields,
        ))

    # 解析关系
    relationships = []
    for rel in model_data.get("relationships", []):
        relationships.append(OSIRelationshipSpec(
            name=rel.get("name", ""),
            from_entity=rel.get("from", ""),
            to_entity=rel.get("to", ""),
            from_columns=rel.get("from_columns", []),
            to_columns=rel.get("to_columns", []),
        ))

    # 解析指标
    metrics = []
    for m in model_data.get("metrics", []):
        expr_data = m.get("expression", {})
        dialects = expr_data.get("dialects", []) if expr_data else []
        expr = dialects[0].get("expression", "") if dialects else ""
        metrics.append(OSIMetricSpec(
            name=m.get("name", ""),
            expression=expr,
            description=m.get("description", ""),
        ))

    # 解析行为
    behavior = model_data.get("behavior", {})

    # 解析 Actions
    actions = []
    for act in behavior.get("actions", []):
        io_schema = act.get("io_schema", {})
        actions.append(OSIActionSpec(
            id=act.get("id", ""),
            name=act.get("name", ""),
            kind=act.get("kind", "query"),
            operation=act.get("operation", "list"),
            entity_name=act.get("entity_name", ""),
            description=act.get("description", ""),
            input_schema=io_schema.get("input_schema", {}),
            labels=act.get("labels", []),
        ))

    # 解析 Rules
    rules = []
    for rule in behavior.get("rules", []):
        rules.append(OSIRuleSpec(
            id=rule.get("id", ""),
            name=rule.get("name", ""),
            description=rule.get("description", ""),
            severity=rule.get("severity", "info"),
            message=rule.get("message", ""),
        ))

    return OSISemanticModel(
        name=model_data.get("name", ""),
        description=model_data.get("description", ""),
        instructions=model_data.get("ai_context", {}).get("instructions", "") if model_data.get("ai_context") else "",
        synonyms=model_data.get("ai_context", {}).get("synonyms", []) if model_data.get("ai_context") else [],
        datasets=datasets,
        relationships=relationships,
        metrics=metrics,
        actions=actions,
        rules=rules,
    )


def convert_to_ontology_spec(osi_model: OSISemanticModel) -> "OntologySpec":
    """将 OSI 模型转换为内部 OntologySpec 格式"""
    from models.ontology import OntologySpec, EntitySpec, PropertySpec, ActionSpec, RuleSpec

    # 转换数据集为实体
    entities = []
    for ds in osi_model.datasets:
        props = [
            PropertySpec(
                name=f.name,
                type=f.type,
                description=f.description,
                required=f.name in ds.primary_key,
            )
            for f in ds.fields
        ]
        entities.append(EntitySpec(
            name=ds.name,
            description=ds.description,
            properties=props,
            labels=[ds.source.split(".")[-1] if "." in ds.source else ""],
            dataset=ds.name,
        ))

    # 转换 Actions
    actions = []
    for act in osi_model.actions:
        actions.append(ActionSpec(
            id=act.id,
            name=act.name,
            description=act.description,
            kind=act.kind,
            operation=act.operation,
            entity_name=act.entity_name,
            input_schema=act.input_schema,
            labels=act.labels,
        ))

    # 转换 Rules
    rules = []
    for rule in osi_model.rules:
        rules.append(RuleSpec(
            id=rule.id,
            name=rule.name,
            description=rule.message or rule.description,
            condition=rule.severity,
            action="",
        ))

    return OntologySpec(
        domain=osi_model.name,
        version="1.0.0",  # OSI 格式没有版本号，使用默认值
        description=osi_model.description,
        entities=entities,
        actions=actions,
        rules=rules,
    )


def convert_to_yaml(osi_model: OSISemanticModel) -> str:
    """将 OSI 模型转换为标准 ontology YAML 格式"""
    ontology = convert_to_ontology_spec(osi_model)
    return ontology.to_yaml()


def get_osi_summary(osi_model: OSISemanticModel) -> str:
    """获取 OSI 模型摘要"""
    lines = [
        f"## OSI 语义模型: {osi_model.name}",
        f"{osi_model.description}",
        "",
    ]

    if osi_model.synonyms:
        lines.append(f"**同义词**: {', '.join(osi_model.synonyms)}")
        lines.append("")

    lines.append(f"### 数据集 ({len(osi_model.datasets)} 个)")
    for ds in osi_model.datasets:
        lines.append(f"- **{ds.name}**: {ds.description}")
        if ds.fields:
            field_names = [f.name for f in ds.fields[:5]]
            if len(ds.fields) > 5:
                field_names.append("...")
            lines.append(f"  - 字段: {', '.join(field_names)}")

    if osi_model.actions:
        lines.append("")
        lines.append(f"### 操作 ({len(osi_model.actions)} 个)")
        for act in osi_model.actions[:10]:
            lines.append(f"- `{act.id}`: {act.name}")

    if osi_model.rules:
        lines.append("")
        lines.append(f"### 规则 ({len(osi_model.rules)} 个)")
        for rule in osi_model.rules:
            lines.append(f"- [{rule.severity}] {rule.name}: {rule.message or rule.description}")

    return "\n".join(lines)
