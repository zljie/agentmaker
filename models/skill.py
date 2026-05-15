"""
技能 (Skill) 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import yaml


@dataclass
class SkillSpec:
    """技能定义"""
    id: str
    name: str
    description: str
    version: str = "0.1"
    action_id: str = ""
    tool: str = ""
    kind: str = "query"  # query, operation, analytics
    operation: str = "list"
    entity_name: str = ""
    labels: List[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 50
    needs_hitl: bool = False

    # Service 层配置
    mode: str = "mock"  # mock, prod
    endpoint: str = ""
    method: str = "POST"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # AI 描述
    ai_description: str = ""
    service_description: str = ""
    governance: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "SkillSpec":
        """从 YAML frontmatter 解析"""
        lines = yaml_str.strip().split("\n")
        frontmatter = []
        in_frontmatter = False
        content_lines = []

        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    continue
            if in_frontmatter:
                frontmatter.append(line)
            else:
                content_lines.append(line)

        meta = yaml.safe_load("\n".join(frontmatter)) or {}
        content = "\n".join(content_lines)

        # 解析 AI/Service/Governance 章节
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        # 解析 Service YAML
        service_yaml = sections.get("Service", "")
        service_data = {}
        if service_yaml:
            try:
                import re
                yaml_match = re.search(r"```yaml\s*(.*?)\s*```", service_yaml, re.DOTALL)
                if yaml_match:
                    service_data = yaml.safe_load(yaml_match.group(1)) or {}
            except:
                pass

        return cls(
            id=meta.get("id", ""),
            name=meta.get("title", meta.get("name", "")),
            description=meta.get("description", ""),
            version=meta.get("version", "0.1"),
            action_id=meta.get("action_id", ""),
            tool=meta.get("tool", ""),
            kind=meta.get("kind", "query"),
            operation=meta.get("operation", "list"),
            entity_name=meta.get("entity_name", ""),
            labels=meta.get("labels", []),
            enabled=meta.get("enabled", True),
            priority=meta.get("priority", 50),
            needs_hitl=meta.get("needs_hitl", False),
            mode=service_data.get("mode", "mock"),
            endpoint=service_data.get("endpoint", ""),
            method=service_data.get("method", "POST"),
            input_schema=service_data.get("input_schema", {}),
            output_schema=service_data.get("output_schema", {}),
            ai_description=sections.get("AI", ""),
            service_description=service_yaml,
            governance=service_data.get("governance", {}),
        )

    def to_yaml(self) -> str:
        """序列化为带 frontmatter 的 Markdown"""
        lines = [
            "---",
            f"id: {self.id}",
            f"title: {self.name}",
            f"version: {self.version}",
            f"action_id: {self.action_id}",
            f"tool: {self.tool}",
            f"kind: {self.kind}",
            f"operation: {self.operation}",
            f"entity_name: {self.entity_name}",
            f"labels: [{', '.join(self.labels)}]",
            f"enabled: {str(self.enabled).lower()}",
            f"priority: {self.priority}",
            f"needs_hitl: {str(self.needs_hitl).lower()}",
            "---",
            "",
            f"## AI\n{self.ai_description}",
            "",
            "## Service",
            "```yaml",
            f"mode: {self.mode}",
            f"endpoint: {self.endpoint}",
            f"method: {self.method}",
            "```",
        ]
        return "\n".join(lines)


class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, SkillSpec] = {}
        self._by_action: Dict[str, SkillSpec] = {}

    def register(self, skill: SkillSpec):
        self._skills[skill.id] = skill
        if skill.action_id:
            self._by_action[skill.action_id] = skill

    def get(self, skill_id: str) -> Optional[SkillSpec]:
        return self._skills.get(skill_id)

    def get_by_action(self, action_id: str) -> Optional[SkillSpec]:
        return self._by_action.get(action_id)

    def list_all(self) -> List[SkillSpec]:
        return list(self._skills.values())

    def list_enabled(self) -> List[SkillSpec]:
        return [s for s in self._skills.values() if s.enabled]

    def render_for_prompt(self) -> str:
        """渲染为 prompt 部分"""
        lines = ["## 可用技能\n"]
        for skill in self.list_enabled():
            lines.append(f"### {skill.name} (`{skill.id}`)")
            lines.append(f"{skill.description}")
            if skill.input_schema.get("properties"):
                lines.append("**参数:**")
                for param, spec in skill.input_schema["properties"].items():
                    desc = spec.get("description", "")
                    lines.append(f"- `{param}`: {desc}")
            lines.append("")
        return "\n".join(lines)
