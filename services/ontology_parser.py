"""
本体解析服务 - 使用 LLM 从本体中提取意图
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from models.intent import IntentSpec
from services.knowledge_graph import KnowledgeGraph, KnowledgeGraphBuilder


@dataclass
class ParsedIntent:
    """解析出的意图"""
    type: str
    name: str
    description: str
    keywords: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    confidence: float = 0.9
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ParseResult:
    """解析结果"""
    intents: List[ParsedIntent]
    knowledge_graph: Dict[str, Any]
    summary: str
    raw_response: str


class OntologyParser:
    """
    本体解析器
    使用 LLM 从本体定义中提取用户意图
    """

    SYSTEM_PROMPT = """你是一个专业的意图识别专家。你的任务是从给定的本体定义中，分析可能的用户意图。

## 输入
你会收到一个本体定义，包含：
- 实体类型及其属性
- 可用的操作/Actions
- 业务规则

## 任务
1. 分析本体定义，识别用户可能的各种意图类型
2. 为每个意图生成：
   - 意图类型（type）：简洁的英文标识符
   - 意图名称（name）：中文描述
   - 意图描述（description）：详细描述这个意图
   - 关键词（keywords）：用于匹配的关键词列表（中文）
   - 对应的操作（actions）：应该调用哪些 action_id
   - 示例问法（examples）：用户可能会怎么问

## 输出格式
请以 JSON 格式输出，结构如下：
```json
{
  "intents": [
    {
      "type": "query_materials",
      "name": "查询物料",
      "description": "用户想要查询物料主数据信息",
      "keywords": ["物料", "材料", "查询物料", "材料列表"],
      "actions": ["materials/list", "materials/get_by_id"],
      "examples": ["查询所有物料", "看看有哪些材料", "给我物料清单"]
    }
  ],
  "summary": "本本体包含 X 个实体，Y 个操作，可以支持 Z 种主要意图..."
}
```

## 注意事项
- 意图应该覆盖主要的用户查询场景
- 每个意图应该至少对应一个 action
- 关键词应该多样化，覆盖不同的表达方式
- 示例问法应该自然、口语化
"""

    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self._client = None

    def _get_client(self):
        """获取 LLM 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.model_config.get("api_key"),
                    base_url=self.model_config.get("api_base", "https://api.deepseek.com/v1"),
                )
            except ImportError:
                try:
                    # Fallback to direct HTTP
                    self._client = "http_client"
                except Exception:
                    return None
        return self._client

    async def parse(self, ontology_yaml: str, ontology_id: str = "unknown") -> ParseResult:
        """
        解析本体并提取意图

        Args:
            ontology_yaml: 本体的 YAML 字符串
            ontology_id: 本体标识符

        Returns:
            ParseResult: 包含解析出的意图和知识图谱
        """
        # 1. 先构建知识图谱
        from models.ontology import OntologySpec
        ontology = OntologySpec.from_yaml(ontology_yaml)
        kg = KnowledgeGraphBuilder.from_ontology(ontology)
        kg_dict = kg.to_dict()
        kg_prompt = kg.render_for_prompt()

        # 2. 调用 LLM 提取意图
        intents = []
        summary = ""
        raw_response = ""

        client = self._get_client()
        if client and client != "http_client":
            try:
                response = client.chat.completions.create(
                    model=self.model_config.get("model_name", "deepseek-chat"),
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": f"## 本体定义\n\n{ontology_yaml}\n\n## 知识图谱\n\n{kg_prompt}"},
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                )
                raw_response = response.choices[0].message.content

                # 3. 解析 LLM 输出
                intents, summary = self._parse_llm_response(raw_response)
            except Exception as e:
                # 如果 LLM 调用失败，返回空结果
                return ParseResult(
                    intents=[],
                    knowledge_graph=kg_dict,
                    summary=f"LLM 调用失败: {str(e)}",
                    raw_response=str(e),
                )
        else:
            # 无 API Key 或客户端不可用，使用规则匹配
            intents = self._rule_based_intent_extraction(ontology)

        # 4. 保存知识图谱到缓存
        from services.knowledge_graph import set_kg_cache
        set_kg_cache(ontology_id, kg)

        return ParseResult(
            intents=intents,
            knowledge_graph=kg_dict,
            summary=summary or f"从本体中提取了 {len(intents)} 个意图",
            raw_response=raw_response,
        )

    def _parse_llm_response(self, content: str) -> tuple[List[ParsedIntent], str]:
        """解析 LLM 响应"""
        intents = []
        summary = ""

        # 提取 JSON 部分
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = content

        # 移除可能的 markdown 代码块
        json_str = re.sub(r'^```\s*', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'\s*```$', '', json_str, flags=re.MULTILINE)
        json_str = json_str.strip()

        try:
            data = json.loads(json_str)

            # 解析意图
            for intent_data in data.get("intents", []):
                intents.append(ParsedIntent(
                    type=intent_data.get("type", ""),
                    name=intent_data.get("name", ""),
                    description=intent_data.get("description", ""),
                    keywords=intent_data.get("keywords", []),
                    actions=intent_data.get("actions", []),
                    examples=intent_data.get("examples", []),
                    confidence=0.9,
                ))

            summary = data.get("summary", "")

        except json.JSONDecodeError as e:
            # JSON 解析失败，尝试规则匹配
            summary = f"JSON 解析失败: {e}"

        return intents, summary

    def _rule_based_intent_extraction(self, ontology) -> List[ParsedIntent]:
        """基于规则提取意图（当 LLM 不可用时）"""
        intents = []

        # 遍历所有 action，生成对应的意图
        for action in getattr(ontology, 'actions', []):
            action_id = getattr(action, 'id', '')
            action_name = getattr(action, 'name', '')
            description = getattr(action, 'description', '')
            operation = getattr(action, 'operation', '')

            # 根据操作类型生成意图
            intent_type = ""
            keywords = []

            if operation == "list":
                intent_type = f"query_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "查询", "列表")
            elif operation == "get":
                intent_type = f"get_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "获取", "查看", "详情")
            elif operation == "create":
                intent_type = f"create_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "创建", "新增", "添加")
            elif operation == "update":
                intent_type = f"update_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "更新", "修改", "编辑")
            elif operation == "delete":
                intent_type = f"delete_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "删除", "移除")
            elif operation == "rank":
                intent_type = f"rank_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "排名", "排序", "Top")
            elif operation == "aggregate":
                intent_type = f"analyze_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "分析", "统计", "汇总")
            else:
                intent_type = f"execute_{action_id.replace('/', '_')}"
                keywords = self._generate_keywords(action_name, description, "执行")

            # 生成意图名称
            intent_name = action_name

            intents.append(ParsedIntent(
                type=intent_type,
                name=intent_name,
                description=description,
                keywords=keywords,
                actions=[action_id],
                examples=[f"我想{action_name}", f"帮我{action_name}"],
                confidence=0.7,  # 规则匹配置信度较低
            ))

        return intents

    def _generate_keywords(self, name: str, description: str, *prefixes) -> List[str]:
        """生成关键词"""
        keywords = []

        for prefix in prefixes:
            keywords.append(f"{prefix}{name}")
            keywords.append(f"{prefix}{description[:10]}")

        # 添加名称和描述的片段
        for word in name:
            if len(word) >= 2:
                keywords.append(word)

        return list(set(keywords))[:10]  # 去重，限制数量


def intent_to_yaml(intents: List[ParsedIntent]) -> str:
    """将意图转换为 YAML 格式"""
    import yaml

    data = {
        "intents": [
            {
                "type": intent.type,
                "name": intent.name,
                "description": intent.description,
                "keywords": intent.keywords,
                "actions": intent.actions,
                "examples": intent.examples,
                "priority": 10,
                "enabled": True,
            }
            for intent in intents
        ]
    }

    return yaml.dump(data, allow_unicode=True, sort_keys=False)


def yaml_to_intents(yaml_str: str) -> List[IntentSpec]:
    """将 YAML 转换为 IntentSpec 列表"""
    import yaml
    data = yaml.safe_load(yaml_str)

    return [
        IntentSpec(
            type=i["type"],
            name=i["name"],
            description=i.get("description", ""),
            keywords=i.get("keywords", []),
            actions=i.get("actions", []),
            examples=i.get("examples", []),
            priority=i.get("priority", 10),
            enabled=i.get("enabled", True),
        )
        for i in data.get("intents", [])
    ]
