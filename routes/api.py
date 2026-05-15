"""
API 路由
"""
import asyncio
import json
from typing import Optional

from fasthtml.common import *

from models.bundle import Bundle, create_sample_bundle, SAMPLE_ONTOLOGY, SAMPLE_INTENTS
from models.intent import IntentSpec
from models.skill import SkillSpec
from models.ontology import OntologySpec
from services.agentscope_runner import MockRunner
from services.storage_service import get_storage_service, RunStatus


# 全局 Bundle 实例
_current_bundle = create_sample_bundle()
_current_ontology = OntologySpec.from_yaml(SAMPLE_ONTOLOGY)
_current_intents = IntentSpec.from_yaml(SAMPLE_INTENTS)


def api_routes(app: FastHTML):
    """注册 API 路由"""

    # ========== 健康检查 ==========
    @app.route("/api/health")
    def health():
        """健康检查"""
        return {
            "status": "ok",
            "service": "NextStudio",
            "version": "0.1.0",
        }

    # ========== 本体管理 ==========
    @app.route("/api/ontologies", methods=["GET"])
    def list_ontologies():
        """获取本体列表"""
        return {
            "ontologies": [
                {
                    "domain": _current_ontology.domain,
                    "version": _current_ontology.version,
                    "description": _current_ontology.description,
                    "entity_count": len(_current_ontology.entities),
                    "action_count": len(_current_ontology.actions),
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
                    "actions": i.actions,
                    "enabled": i.enabled,
                    "priority": i.priority,
                }
                for i in _current_intents
            ]
        }

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
        use_mock = data.get("use_mock", True)
        model_config = data.get("model_config", {})

        if not message:
            return {"error": "Message is required"}, 400

        storage = get_storage_service()
        run_id = await storage.create_run(message)
        await storage.update_status(run_id, RunStatus.RUNNING)

        # 启动后台运行
        asyncio.create_task(_run_agent(run_id, message, use_mock, model_config))

        return {"run_id": run_id}

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


async def _run_agent(run_id: str, message: str, use_mock: bool, model_config: dict):
    """后台运行 Agent"""
    storage = get_storage_service()

    try:
        # 选择 Runner
        if use_mock:
            runner = MockRunner(
                bundle=_current_bundle,
                model_config=model_config,
                run_id=run_id,
            )
        else:
            from services.agentscope_runner import AgentScopeRunner
            runner = AgentScopeRunner(
                bundle=_current_bundle,
                model_config=model_config,
                run_id=run_id,
            )
            await runner.initialize()

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
