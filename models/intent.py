"""
意图 (Intent) 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml


@dataclass
class IntentClassification:
    """意图分类结果"""
    type: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)


@dataclass
class IntentSpec:
    """意图定义"""
    type: str
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)  # 正则表达式
    actions: List[str] = field(default_factory=list)  # 关联的 Action ID
    examples: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 50

    @classmethod
    def from_yaml(cls, yaml_str: str) -> List["IntentSpec"]:
        """从 YAML 解析意图列表"""
        data = yaml.safe_load(yaml_str)
        intents = []
        for item in data.get("intents", []):
            intents.append(cls(
                type=item["type"],
                name=item["name"],
                description=item.get("description", ""),
                keywords=item.get("keywords", []),
                patterns=item.get("patterns", []),
                actions=item.get("actions", []),
                examples=item.get("examples", []),
                enabled=item.get("enabled", True),
                priority=item.get("priority", 50),
            ))
        return intents

    def to_yaml(self) -> str:
        return yaml.dump({
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "patterns": self.patterns,
            "actions": self.actions,
            "examples": self.examples,
            "enabled": self.enabled,
            "priority": self.priority,
        }, allow_unicode=True)


class IntentRouter:
    """意图路由 - 规则匹配"""

    def __init__(self, intents: List[IntentSpec]):
        self.intents = [i for i in intents if i.enabled]
        self.intents.sort(key=lambda x: x.priority, reverse=True)
        self._build_patterns()

    def _build_patterns(self):
        import re
        self.compiled_patterns = {}
        for intent in self.intents:
            self.compiled_patterns[intent.type] = [
                re.compile(p, re.IGNORECASE) for p in intent.patterns
            ]

    def classify(self, message: str) -> IntentClassification:
        """
        对用户消息进行意图分类
        规则: 优先关键词匹配 > 正则匹配 > 默认
        """
        message_lower = message.lower()

        # 关键词匹配
        for intent in self.intents:
            score = 0
            matched_keywords = []
            for kw in intent.keywords:
                if kw.lower() in message_lower:
                    score += 1
                    matched_keywords.append(kw)

            if score > 0:
                confidence = min(score / max(len(intent.keywords), 1) * 0.8 + 0.2, 1.0)
                return IntentClassification(
                    type=intent.type,
                    confidence=confidence,
                    actions=intent.actions,
                )

        # 正则匹配
        for intent in self.intents:
            for pattern in self.compiled_patterns.get(intent.type, []):
                if pattern.search(message):
                    return IntentClassification(
                        type=intent.type,
                        confidence=0.7,
                        actions=intent.actions,
                    )

        # 默认: query 类型
        return IntentClassification(
            type="query",
            confidence=0.5,
            actions=[],
        )


# 示例意图配置
SAMPLE_INTENTS = """
intents:
  - type: query_materials
    name: 查询物料
    description: 查询物料主数据
    keywords:
      - 物料
      - 材料
      - 产品
      - 物料编码
      - 物料名称
    patterns:
      - ".*物料.*"
      - ".*材料.*列表"
    actions:
      - materials/list
      - materials/get_by_id
    examples:
      - "查询今日待审批的采购申请单，如果金额大于1000的需要人工审核"
      - "物料列表"
      - "帮我看看物料有哪些"

  - type: query_suppliers
    name: 查询供应商
    description: 查询供应商主数据
    keywords:
      - 供应商
      - 供应商列表
      - 供应商编码
    patterns:
      - ".*供应商.*"
    actions:
      - suppliers/list
    examples:
      - "查询供应商"
      - "供应商列表"

  - type: query_orders
    name: 查询采购订单
    description: 查询采购订单
    keywords:
      - 订单
      - 采购订单
      - PO
      - purchase.order
    patterns:
      - ".*订单.*"
      - ".*PO.*"
    actions:
      - purchase_orders/list
    examples:
      - "查询采购订单"
      - "最近有哪些订单"

  - type: analytics_demand
    name: 需求分析
    description: 分析物料需求
    keywords:
      - 需求
      - 需求分析
      - 需求排名
      - top物料
    patterns:
      - ".*需求.*"
      - ".*排名.*"
    actions:
      - analytics/top_materials_by_demand
    examples:
      - "需求量最大的物料是什么"
      - "本月需求排名"

  - type: analytics_supplier
    name: 供应商分析
    description: 分析供应商绩效
    keywords:
      - 供应商绩效
      - 供应商分析
      - 交付
      - on.time
    patterns:
      - ".*供应商.*绩效.*"
      - ".*交付.*"
    actions:
      - analytics/supplier_performance
    examples:
      - "供应商交付情况如何"
      - "哪些供应商绩效最好"
"""
