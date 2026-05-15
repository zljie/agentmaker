"""
数据模型层
"""
from .ontology import EntitySpec, ActionSpec, OntologySpec
from .intent import IntentSpec, IntentClassification
from .skill import SkillSpec, SkillRegistry
from .connector import ConnectorConfig, ConnectorAction
from .bundle import Bundle, AgentConfig, RuntimeConfig

__all__ = [
    "EntitySpec",
    "ActionSpec",
    "OntologySpec",
    "IntentSpec",
    "IntentClassification",
    "SkillSpec",
    "SkillRegistry",
    "ConnectorConfig",
    "ConnectorAction",
    "Bundle",
    "AgentConfig",
    "RuntimeConfig",
]
