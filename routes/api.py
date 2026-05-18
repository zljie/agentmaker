"""
API 路由
"""
import asyncio
import json
import uuid
import yaml
from typing import Optional
from datetime import date

from fasthtml.common import *

from models.bundle import Bundle, create_sample_bundle, SAMPLE_ONTOLOGY, SAMPLE_INTENTS
from models.intent import IntentSpec
from models.skill import SkillSpec
from models.ontology import OntologySpec
from services.agentscope_runner import MockRunner
from services.storage_service import get_storage_service, RunStatus
from services.database import get_database_service
from config import LLM_CONFIG


# 全局 Bundle 实例
_current_bundle = create_sample_bundle()
_current_ontology = OntologySpec.from_yaml(SAMPLE_ONTOLOGY)
_current_intents = IntentSpec.from_yaml(SAMPLE_INTENTS)


def api_routes(app: FastHTML):
    """注册 API 路由"""

    # ========== 健康检查 ==========
    @app.route("/api/health")
    def health(req):
        """健康检查"""
        llm_ready = bool(LLM_CONFIG.get("api_key"))
        db = get_database_service()

        return {
            "status": "ok",
            "service": "NextStudio",
            "version": "0.1.0",
            "llm_configured": llm_ready,
            "llm_model": LLM_CONFIG.get("model_name", ""),
            "database_connected": db.is_connected,
        }

    # ========== 本体管理 ==========
    @app.route("/api/ontologies", methods=["GET"])
    def list_ontologies():
        """获取本体列表"""
        db = get_database_service()

        if db.is_connected:
            ontologies = db.list_ontologies()
            return {
                "ontologies": [
                    {
                        "id": o.get("id"),
                        "name": o.get("name"),
                        "domain": o.get("name"),
                        "version": o.get("version", "1.0.0"),
                        "description": o.get("description", ""),
                        "created_at": o.get("created_at"),
                    }
                    for o in ontologies
                ]
            }
        else:
            # Fallback to sample ontology
            return {
                "ontologies": [
                    {
                        "domain": _current_ontology.domain,
                        "version": _current_ontology.version,
                        "description": _current_ontology.description,
                        "entity_count": len(_current_ontology.entities),
                        "action_count": len(_current_ontology.actions),
                        "is_sample": True,
                    }
                ]
            }

    @app.route("/api/ontologies/current")
    def get_current_ontology():
        """获取当前本体详情"""
        return {
            "domain": _current_ontology.domain,
            "version": _current_ontology.version,
            "description": _current_ontology.description,
            "entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "labels": e.labels,
                    "dataset": e.dataset,
                    "properties": [
                        {"name": p.name, "type": p.type, "description": p.description}
                        for p in e.properties
                    ],
                }
                for e in _current_ontology.entities
            ],
            "actions": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "kind": a.kind,
                    "operation": a.operation,
                    "entity_name": a.entity_name,
                    "labels": a.labels,
                }
                for a in _current_ontology.actions
            ],
        }

    @app.route("/api/ontologies/raw")
    def get_ontology_raw():
        """获取原始 YAML"""
        return {"yaml": SAMPLE_ONTOLOGY}

    @app.route("/api/ontologies/upload", methods=["POST"])
    async def upload_ontology(req):
        """上传 ontology 文件 (YAML 或 JSON)"""
        try:
            # 解析 multipart/form-data
            form_data = await req.form()
            file = form_data.get("file")

            if not file:
                return {"error": "No file provided"}, 400

            # 读取文件内容
            file_content = await file.read()
            content_str = file_content.decode("utf-8")

            # 检测文件类型并解析
            filename = file.filename or ""
            if filename.endswith(".json"):
                try:
                    data = json.loads(content_str)
                    content_str = yaml.dump(data, allow_unicode=True, sort_keys=False)
                except json.JSONDecodeError as e:
                    return {"error": f"Invalid JSON: {e}"}, 400
            elif filename.endswith((".yaml", ".yml")):
                pass
            else:
                return {"error": "Unsupported file type. Please upload .yaml, .yml, or .json file."}, 400

            # 检测是否为 OSI 格式
            from services.osi_parser import is_osi_format, parse_osi_yaml, convert_to_yaml, get_osi_summary

            is_osi = is_osi_format(content_str)
            original_yaml = content_str  # 保存原始格式

            if is_osi:
                # 解析 OSI 格式并转换为标准格式
                osi_model = parse_osi_yaml(content_str)
                content_str = convert_to_yaml(osi_model)
                osi_summary = get_osi_summary(osi_model)
            else:
                osi_summary = None

            # 解析验证 ontology
            try:
                ontology = OntologySpec.from_yaml(content_str)
            except Exception as e:
                if is_osi:
                    return {"error": f"OSI format parsed but conversion failed: {e}"}, 400
                return {"error": f"Invalid ontology format: {e}"}, 400

            # 存储到数据库
            db = get_database_service()
            name = form_data.get("name", ontology.domain)

            if db.is_connected:
                db_ontology = db.create_ontology(
                    name=name,
                    description=ontology.description,
                    yaml_content=content_str,
                    version=ontology.version,
                )
                if db_ontology:
                    result = {
                        "id": db_ontology["id"],
                        "name": db_ontology["name"],
                        "domain": ontology.domain,
                        "version": ontology.version,
                        "description": ontology.description,
                        "entity_count": len(ontology.entities),
                        "action_count": len(ontology.actions),
                        "created_at": db_ontology["created_at"],
                    }
                    if is_osi:
                        result["is_osi_format"] = True
                        result["osi_summary"] = osi_summary
                    return result, 201
                else:
                    return {"error": "Failed to save ontology to database"}, 500
            else:
                # 无数据库时，返回解析结果（不保存）
                result = {
                    "name": name,
                    "domain": ontology.domain,
                    "version": ontology.version,
                    "description": ontology.description,
                    "entity_count": len(ontology.entities),
                    "action_count": len(ontology.actions),
                    "warning": "No database connected. Ontology not persisted.",
                }
                if is_osi:
                    result["is_osi_format"] = True
                    result["osi_summary"] = osi_summary
                return result, 201

        except Exception as e:
            return {"error": str(e)}, 500

    @app.route("/api/ontologies/parse", methods=["POST"])
    async def parse_ontology(req):
        """
        解析本体，提取意图并构建知识图谱
        POST /api/ontologies/parse
        Body: { "yaml_content": "...", "ontology_id": "optional_id" }
        """
        try:
            from services.ontology_parser import OntologyParser
            from services.knowledge_graph import get_kg_cache, set_kg_cache, KnowledgeGraphBuilder

            data = await req.json()
            yaml_content = data.get("yaml_content")
            ontology_id = data.get("ontology_id", "current")

            if not yaml_content:
                # 如果没有提供 yaml，从当前本体获取
                yaml_content = SAMPLE_ONTOLOGY

            # 使用 LLM 解析本体
            parser = OntologyParser(LLM_CONFIG)
            result = await parser.parse(yaml_content, ontology_id)

            # 保存知识图谱到缓存
            kg = KnowledgeGraphBuilder.from_ontology(
                OntologySpec.from_yaml(yaml_content)
            )
            set_kg_cache(ontology_id, kg)

            return {
                "intents": [i.to_dict() for i in result.intents],
                "knowledge_graph": result.knowledge_graph,
                "summary": result.summary,
                "kg_stats": result.knowledge_graph.get("stats", {}),
            }

        except Exception as e:
            return {"error": str(e)}, 500

    @app.route("/api/ontologies/knowledge-graph")
    async def get_knowledge_graph():
        """获取当前本体的知识图谱"""
        from services.knowledge_graph import get_kg_cache

        kg = get_kg_cache("current")
        if kg:
            return kg.to_dict()
        else:
            # 如果没有缓存，构建一个
            from services.knowledge_graph import KnowledgeGraphBuilder
            kg = KnowledgeGraphBuilder.from_ontology(_current_ontology)
            return kg.to_dict()

    @app.route("/api/ontologies/knowledge-graph/render")
    async def render_knowledge_graph():
        """获取知识图谱的 prompt 格式"""
        from services.knowledge_graph import get_kg_cache

        kg = get_kg_cache("current")
        if kg:
            return {"prompt": kg.render_for_prompt()}
        else:
            return {"prompt": "No knowledge graph available"}

    @app.route("/api/ontologies/{ontology_id}", methods=["GET"])
    async def get_ontology_by_id(ontology_id: str):
        """根据 ID 获取 ontology"""
        db = get_database_service()

        if db.is_connected:
            db_ontology = db.get_ontology(ontology_id)
            if not db_ontology:
                return {"error": "Ontology not found"}, 404

            # 解析 yaml_content
            try:
                ontology = OntologySpec.from_yaml(db_ontology["yaml_content"])
                return {
                    "id": db_ontology["id"],
                    "name": db_ontology["name"],
                    "domain": ontology.domain,
                    "version": ontology.version,
                    "description": ontology.description,
                    "entities": [
                        {
                            "name": e.name,
                            "description": e.description,
                            "labels": e.labels,
                            "properties": [
                                {"name": p.name, "type": p.type, "description": p.description}
                                for p in e.properties
                            ],
                        }
                        for e in ontology.entities
                    ],
                    "actions": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "description": a.description,
                            "kind": a.kind,
                            "operation": a.operation,
                            "entity_name": a.entity_name,
                        }
                        for a in ontology.actions
                    ],
                    "created_at": db_ontology["created_at"],
                    "updated_at": db_ontology["updated_at"],
                }
            except Exception as e:
                return {"error": f"Failed to parse ontology: {e}"}, 500
        else:
            return {"error": "Database not connected"}, 503

    @app.route("/api/ontologies/{ontology_id}", methods=["DELETE"])
    async def delete_ontology_by_id(ontology_id: str):
        """删除 ontology"""
        db = get_database_service()

        if not db.is_connected:
            return {"error": "Database not connected"}, 503

        success = db.delete_ontology(ontology_id)
        if success:
            return {"status": "ok", "message": "Ontology deleted"}
        else:
            return {"error": "Failed to delete ontology"}, 500

    # ========== 意图管理 ==========
    @app.route("/api/intents", methods=["GET"])
    def list_intents():
        """获取意图列表"""
        return {
            "intents": [
                {
                    "type": i.type,
                    "name": i.name,
                    "description": i.description,
                    "keywords": i.keywords,
                    "patterns": i.patterns,
                    "actions": i.actions,
                    "examples": i.examples,
                    "enabled": i.enabled,
                    "priority": i.priority,
                }
                for i in _current_intents
            ]
        }

    @app.route("/api/intents", methods=["POST"])
    async def create_intent(req):
        """创建意图"""
        global _current_intents

        data = await req.json()

        required_fields = ["type", "name"]
        for field in required_fields:
            if not data.get(field):
                return {"error": f"Missing required field: {field}"}, 400

        # 检查是否已存在
        if any(i.type == data["type"] for i in _current_intents):
            return {"error": f"Intent with type '{data['type']}' already exists"}, 400

        new_intent = IntentSpec(
            type=data["type"],
            name=data["name"],
            description=data.get("description", ""),
            keywords=data.get("keywords", []),
            patterns=data.get("patterns", []),
            actions=data.get("actions", []),
            examples=data.get("examples", []),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 50),
        )

        _current_intents.append(new_intent)

        return {
            "status": "ok",
            "intent": {
                "type": new_intent.type,
                "name": new_intent.name,
                "description": new_intent.description,
                "keywords": new_intent.keywords,
                "actions": new_intent.actions,
                "enabled": new_intent.enabled,
                "priority": new_intent.priority,
            }
        }, 201

    @app.route("/api/intents/{intent_type}", methods=["PUT"])
    async def update_intent(req, intent_type: str):
        """更新意图"""
        global _current_intents

        data = await req.json()

        # 查找意图
        intent_index = None
        for i, intent in enumerate(_current_intents):
            if intent.type == intent_type:
                intent_index = i
                break

        if intent_index is None:
            return {"error": "Intent not found"}, 404

        intent = _current_intents[intent_index]

        # 更新字段
        if "type" in data and data["type"] != intent_type:
            # 检查新 type 是否已存在
            if any(i.type == data["type"] for i in _current_intents if i.type != intent_type):
                return {"error": f"Intent with type '{data['type']}' already exists"}, 400

        intent.type = data.get("type", intent.type)
        intent.name = data.get("name", intent.name)
        intent.description = data.get("description", intent.description)
        intent.keywords = data.get("keywords", intent.keywords)
        intent.patterns = data.get("patterns", intent.patterns)
        intent.actions = data.get("actions", intent.actions)
        intent.examples = data.get("examples", intent.examples)
        intent.enabled = data.get("enabled", intent.enabled)
        intent.priority = data.get("priority", intent.priority)

        return {
            "status": "ok",
            "intent": {
                "type": intent.type,
                "name": intent.name,
                "description": intent.description,
                "keywords": intent.keywords,
                "actions": intent.actions,
                "enabled": intent.enabled,
                "priority": intent.priority,
            }
        }

    @app.route("/api/intents/{intent_type}", methods=["DELETE"])
    async def delete_intent(intent_type: str):
        """删除意图"""
        global _current_intents

        # 查找并删除
        for i, intent in enumerate(_current_intents):
            if intent.type == intent_type:
                _current_intents.pop(i)
                return {"status": "ok", "message": "Intent deleted"}

        return {"error": "Intent not found"}, 404

    @app.route("/api/intents/raw")
    def get_intents_raw():
        """获取原始 YAML"""
        return {"yaml": SAMPLE_INTENTS}

    # ========== 技能管理 ==========
    @app.route("/api/skills", methods=["GET"])
    def list_skills():
        """获取技能列表"""
        return {
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "action_id": s.action_id,
                    "kind": s.kind,
                    "enabled": s.enabled,
                    "priority": s.priority,
                }
                for s in _current_bundle.skills
            ]
        }

    # ========== 连接器管理 ==========
    @app.route("/api/connectors", methods=["GET"])
    def list_connectors():
        """获取连接器列表"""
        connectors = _current_bundle.connector_registry.list_all()
        return {
            "connectors": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "category": c.category,
                    "enabled": c.enabled,
                    "is_mock": c.is_mock,
                    "action_count": len(c.actions),
                }
                for c in connectors
            ]
        }

    @app.route("/api/connectors/{connector_id}/actions")
    def get_connector_actions(connector_id: str):
        """获取连接器的 Action"""
        connector = _current_bundle.connector_registry.get(connector_id)
        if not connector:
            return {"error": "Connector not found"}, 404

        return {
            "actions": [
                {
                    "id": a.id,
                    "name": a.name,
                    "description": a.description,
                    "endpoint": a.endpoint,
                    "method": a.method,
                }
                for a in connector.actions
            ]
        }

    # ========== Bundle ==========
    @app.route("/api/bundle")
    def get_bundle():
        """获取当前 Bundle"""
        return _current_bundle.to_dict()

    # ========== 运行管理 ==========
    @app.route("/api/runs", methods=["GET"])
    def list_runs():
        """获取运行历史"""
        storage = get_storage_service()
        runs = asyncio.run(storage.list_runs())

        return {
            "runs": [
                {
                    "run_id": r.run_id,
                    "message": r.message,
                    "status": r.status.value,
                    "created_at": r.created_at,
                    "completed_at": r.completed_at,
                }
                for r in runs
            ]
        }

    @app.route("/api/runs", methods=["POST"])
    async def create_run(req):
        """创建并启动运行"""
        data = await req.json()
        message = data.get("message", "")
        use_mock = data.get("use_mock", None)  # None = auto-detect
        model_config = data.get("model_config", {})

        if not message:
            return {"error": "Message is required"}, 400

        # Auto-detect: use real LLM if API key is available and use_mock not explicitly set
        if use_mock is None:
            use_mock = not bool(LLM_CONFIG.get("api_key"))

        storage = get_storage_service()
        run_id = await storage.create_run(message)
        await storage.update_status(run_id, RunStatus.RUNNING)

        # 启动后台运行
        asyncio.create_task(_run_agent(run_id, message, use_mock, model_config))

        return {"run_id": run_id, "use_mock": use_mock}

    @app.route("/api/runs/{run_id}/events")
    async def stream_events(run_id: str):
        """SSE 流式事件"""
        storage = get_storage_service()

        async def event_generator():
            async for event in storage.stream_events(run_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: {\"type\": \"stream_end\"}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.route("/api/runs/{run_id}/abort", methods=["POST"])
    async def abort_run(run_id: str):
        """中止运行"""
        storage = get_storage_service()
        await storage.update_status(run_id, RunStatus.ABORTED)
        await storage.add_event(run_id, {"type": "aborted", "data": {"reason": "User aborted"}})
        return {"status": "ok"}

    @app.route("/api/runs/{run_id}", methods=["GET"])
    async def get_run(run_id: str):
        """获取运行详情"""
        storage = get_storage_service()
        run = await storage.get_run(run_id)

        if not run:
            return {"error": "Run not found"}, 404

        return {
            "run_id": run.run_id,
            "message": run.message,
            "status": run.status.value,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
            "events": run.events,
            "result": run.result,
        }

    # ========== 统计 ==========
    @app.route("/api/stats")
    def get_stats():
        """获取统计信息"""
        return {
            "ontologies": 1,
            "intents": len(_current_intents),
            "skills": len(_current_bundle.skills),
            "connectors": len(_current_bundle.connector_registry.list_all()),
            "agents": 1,
        }

    # ========== 采购审批 ==========
    @app.route("/api/approvals", methods=["POST"])
    async def submit_approval(req):
        """提交审批结果"""
        from services.procurement_workflow import get_workflow_engine

        data = await req.json()
        request_no = data.get("request_no")
        action = data.get("action")
        comment = data.get("comment", "")

        if not request_no or not action:
            return {"error": "Missing required fields: request_no, action"}, 400

        if action not in ["approve", "reject"]:
            return {"error": "Invalid action. Must be 'approve' or 'reject'"}, 400

        engine = get_workflow_engine()
        result = engine.submit_approval(request_no, action, comment)

        if result.get("success"):
            return result
        else:
            return {"error": result.get("error", "Unknown error")}, 500

    @app.route("/api/approvals/pending")
    def get_pending_approvals():
        """获取待审批列表"""
        from services.procurement_workflow import get_workflow_engine

        engine = get_workflow_engine()
        requests = engine._query_pending_requests(
            date_from=date.today().isoformat(),
            date_to=date.today().isoformat(),
            status="pending"
        )

        analysis = engine.analyze_requests(requests)

        return {
            "pending": analysis["hitl_approve"],
            "auto_approved": analysis["auto_approve"],
            "summary": analysis["summary"],
        }

    @app.route("/api/approvals/history")
    def get_approval_history():
        """获取审批历史（已处理的）"""
        from services.procurement_workflow import get_workflow_engine

        engine = get_workflow_engine()
        all_requests = engine._mock_requests

        # 过滤出已处理的（approved/rejected）
        processed = [
            {
                "request_no": req.request_no,
                "title": req.title,
                "applicant": req.applicant,
                "department": req.department,
                "amount": req.amount,
                "status": req.status,
                "request_date": req.request_date,
            }
            for req in all_requests
            if req.status in ["approved", "rejected"]
        ]

        return {"history": processed}

    @app.route("/api/approvals/line", methods=["POST"])
    async def approve_line_item(req):
        """审批单个明细行"""
        from services.procurement_workflow import get_workflow_engine

        data = await req.json()
        request_no = data.get("request_no")
        line_id = data.get("line_id")
        action = data.get("action")
        comment = data.get("comment", "")

        if not request_no or not line_id or not action:
            return {"error": "Missing required fields: request_no, line_id, action"}, 400

        if action not in ["approve", "reject"]:
            return {"error": "Invalid action. Must be 'approve' or 'reject'"}, 400

        if not comment:
            comment = "审批通过" if action == "approve" else "审批拒绝"

        engine = get_workflow_engine()
        result = engine.approve_line_item(request_no, line_id, action, comment)

        if result.get("success"):
            return result
        else:
            return {"error": result.get("error", "Unknown error")}, 500

    @app.route("/api/approvals/<request_no>")
    def get_approval_detail(request_no: str):
        """获取申请单详情"""
        from services.procurement_workflow import get_workflow_engine

        engine = get_workflow_engine()
        request_data = engine.get_request_with_lines(request_no)

        if request_data:
            return {"request": request_data}
        else:
            return {"error": "Request not found"}, 404


async def _run_agent(run_id: str, message: str, use_mock: bool, model_config: dict):
    """后台运行 Agent"""
    storage = get_storage_service()

    try:
        # 合并全局配置和请求配置
        merged_config = {**LLM_CONFIG, **model_config}

        # 选择 Runner
        if use_mock:
            runner = MockRunner(
                bundle=_current_bundle,
                model_config=merged_config,
                run_id=run_id,
            )
        else:
            from services.agentscope_runner import AgentScopeRunner
            runner = AgentScopeRunner(
                bundle=_current_bundle,
                model_config=merged_config,
                run_id=run_id,
            )

        # 运行并收集事件
        final_content = ""
        async for event in runner.run_stream(message):
            await storage.add_event(run_id, {
                "type": event.type,
                "data": event.data,
                "iteration": event.iteration,
                "step": event.step,
            })

            if event.type == "final_delta":
                final_content = event.data.get("content", "")

        # 保存结果
        await storage.set_result(run_id, {"content": final_content})
        await storage.update_status(run_id, RunStatus.COMPLETED)

    except Exception as e:
        await storage.add_event(run_id, {
            "type": "error",
            "data": {"error": str(e)},
        })
        await storage.update_status(run_id, RunStatus.ERROR)
