"""
AgentScope Runner - 运行 Agent 并提供 SSE 流式输出
"""
import asyncio
import json
import uuid
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass

from models.bundle import Bundle, create_sample_bundle
from models.connector import MockConnector
from services.procurement_workflow import (
    ProcurementWorkflowEngine,
    get_workflow_engine,
    TaskType,
    WorkflowTask,
)


@dataclass
class RunEvent:
    """运行事件"""
    type: str
    data: Dict[str, Any]
    iteration: int = 0
    step: int = 0


class AgentScopeRunner:
    """
    AgentScope 运行器
    封装 ReActAgent，提供 SSE 流式输出

    注意: 此版本为简化实现，需要配置 LLM API Key 才能真正运行
    """

    def __init__(
        self,
        bundle: Bundle,
        model_config: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        self.run_id = run_id or str(uuid.uuid4())
        self.bundle = bundle
        self.bundle.initialize()

        self.model_config = model_config
        self._should_abort = False

    async def run_stream(self, user_message: str) -> AsyncGenerator[RunEvent, None]:
        """
        运行 Agent 并产生 SSE 事件流
        """
        yield RunEvent(
            type="run_started",
            data={"run_id": self.run_id, "message": user_message},
            iteration=0,
            step=0,
        )

        # 意图识别
        intent_result = self.bundle.classify_intent(user_message)
        yield RunEvent(
            type="intent",
            data={
                "type": intent_result.type,
                "confidence": intent_result.confidence,
                "actions": intent_result.actions,
            },
            iteration=0,
            step=1,
        )

        # 检查是否配置了 API Key
        api_key = self.model_config.get("api_key", "")
        if not api_key:
            # 使用 Mock 模式
            async for event in MockRunner(self.bundle, self.model_config, self.run_id).run_stream(user_message):
                if event.type != "run_started":
                    yield event
            return

        # 尝试使用 AgentScope
        try:
            import agentscope
            from agentscope.agent import ReActAgent
            from agentscope.message import Msg
            from agentscope.memory import InMemoryMemory
            from agentscope.tool import Toolkit
            from agentscope.formatter import OpenAIChatFormatter
            from agentscope.model import OpenAIChatModel

            # 初始化
            if not hasattr(agentscope, '_global_config') or not agentscope._global_config:
                agentscope.init()

            # 创建模型
            # 使用配置中的 model_name，默认为 deepseek-chat
            model_name = self.model_config.get("model_name", "deepseek-chat")
            api_key = self.model_config.get("api_key", "")
            api_base = self.model_config.get("api_base", "https://api.deepseek.com/v1")

            # 如果 model_name 包含 "deepseek"，使用 DeepSeek 的 API base
            if "deepseek" in model_name.lower():
                api_base = self.model_config.get("api_base", "https://api.deepseek.com/v1")

            model = OpenAIChatModel(
                model_name=model_name,
                api_key=api_key,
                api_base=api_base,
                temperature=self.model_config.get("temperature", 0.7),
            )

            # 创建工具集
            toolkit = await self._create_toolkit()
            memory = InMemoryMemory()

            # 创建 Agent
            agent = ReActAgent(
                name=self.bundle.agent_config.name,
                sys_prompt=self.bundle.build_system_prompt(),
                model=model,
                memory=memory,
                toolkit=toolkit,
                max_iters=self.bundle.runtime.max_iters,
                formatter=OpenAIChatFormatter(),
            )

            yield RunEvent(
                type="prelude_delta",
                data={"content": "正在连接 AgentScope..."},
                iteration=0,
                step=2,
            )

            # 运行
            user_msg = Msg("user", user_message, role="user")
            response = await agent(user_msg)

            content = ""
            if isinstance(response, dict):
                content = response.get("content", str(response))
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)

            if content:
                yield RunEvent(
                    type="final_delta",
                    data={"content": content},
                    iteration=0,
                    step=3,
                )

            yield RunEvent(
                type="done",
                data={"timestamp": self._get_timestamp()},
                iteration=0,
                step=4,
            )

        except ImportError as e:
            yield RunEvent(
                type="error",
                data={"error": f"AgentScope 导入失败: {e}"},
                iteration=0,
                step=0,
            )
        except Exception as e:
            yield RunEvent(
                type="error",
                data={"error": str(e), "type": type(e).__name__},
                iteration=0,
                step=0,
            )

    async def _create_toolkit(self):
        """创建工具集"""
        from agentscope.tool import Toolkit, function_to_tool

        toolkit = Toolkit()
        mock_conn = self.bundle.connector_registry.get_mock_connector()

        for action in mock_conn.config.actions:
            tool_func = self._make_tool_function(action.id, mock_conn)
            toolkit.register_tool_function(tool_func)

        return toolkit

    def _make_tool_function(self, action_id: str, mock_conn: MockConnector):
        """创建工具函数"""
        from agentscope.tool import function_to_tool

        action = mock_conn.get_action(action_id)
        desc = action.description if action else f"执行 {action_id}"
        endpoint = action.endpoint if action else ""

        async def tool_func(**kwargs) -> str:
            result = await mock_conn.execute(action_id, kwargs)
            return json.dumps(result, ensure_ascii=False, indent=2)

        tool_func.__name__ = action_id.replace("/", "_")
        tool_func.__doc__ = f"{desc}\n\nEndpoint: {endpoint}"

        return function_to_tool(tool_func)

    def abort(self):
        """中止运行"""
        self._should_abort = True

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class MockRunner:
    """
    Mock 运行器 - 不依赖真实 LLM API
    用于演示和测试

    包含完整的采购审批工作流支持:
    1. 日期转换（内部函数，减少 token）
    2. 意图识别
    3. 任务规划
    4. 分步执行
    5. 自动审批 / HITL 审批
    """

    def __init__(
        self,
        bundle: Bundle,
        model_config: Dict[str, Any],
        run_id: Optional[str] = None
    ):
        self.run_id = run_id or str(uuid.uuid4())
        self.bundle = bundle
        self._should_abort = False
        # 采购审批工作流引擎
        self.workflow_engine = get_workflow_engine()

    async def run_stream(self, user_message: str) -> AsyncGenerator[RunEvent, None]:
        """Mock 流式运行"""
        yield RunEvent(
            type="run_started",
            data={"run_id": self.run_id, "message": user_message},
            iteration=0,
            step=0,
        )

        # 模拟意图识别
        await asyncio.sleep(0.3)
        intent_result = self.bundle.classify_intent(user_message)
        yield RunEvent(
            type="intent",
            data={
                "type": intent_result.type,
                "confidence": intent_result.confidence,
                "actions": intent_result.actions,
            },
            iteration=0,
            step=1,
        )

        # 检测是否为采购审批场景
        if self._is_procurement_workflow(user_message):
            async for event in self._run_procurement_workflow(user_message):
                yield event
            return

        # 原有逻辑保持不变...
        # 模拟思考
        await asyncio.sleep(0.5)
        yield RunEvent(
            type="prelude_delta",
            data={"content": "收到您的请求，让我分析一下..."},
            iteration=0,
            step=2,
        )

        # 模拟工具调用
        msg_lower = user_message.lower()

        if any(kw in msg_lower for kw in ["物料", "材料", "查询所有"]):
            await asyncio.sleep(0.8)
            yield RunEvent(
                type="step_start",
                data={
                    "tool": "materials_list",
                    "action": "materials/list",
                    "args": {"plant_id": "P100", "page": 1},
                },
                iteration=0,
                step=3,
            )

            await asyncio.sleep(0.6)
            yield RunEvent(
                type="step_end",
                data={
                    "tool": "materials_list",
                    "status": "ok",
                    "output": {
                        "total": 5,
                        "data": [
                            {"material_id": "M001", "material_name": "钢板", "unit": "吨"},
                            {"material_id": "M002", "material_name": "螺丝", "unit": "个"},
                            {"material_id": "M003", "material_name": "电机", "unit": "台"},
                        ]
                    }
                },
                iteration=0,
                step=4,
            )

        elif any(kw in msg_lower for kw in ["供应商"]):
            await asyncio.sleep(0.8)
            yield RunEvent(
                type="step_start",
                data={
                    "tool": "suppliers_list",
                    "action": "suppliers/list",
                    "args": {},
                },
                iteration=0,
                step=3,
            )

            await asyncio.sleep(0.6)
            yield RunEvent(
                type="step_end",
                data={
                    "tool": "suppliers_list",
                    "status": "ok",
                    "output": {
                        "total": 4,
                        "data": [
                            {"supplier_id": "S001", "supplier_name": "华东钢材公司"},
                            {"supplier_id": "S002", "supplier_name": "精密螺丝厂"},
                            {"supplier_id": "S003", "supplier_name": "电机科技"},
                        ]
                    }
                },
                iteration=0,
                step=4,
            )

        elif any(kw in msg_lower for kw in ["订单", "po"]):
            await asyncio.sleep(0.8)
            yield RunEvent(
                type="step_start",
                data={
                    "tool": "orders_list",
                    "action": "purchase_orders/list",
                    "args": {"status": "已发货"},
                },
                iteration=0,
                step=3,
            )

            await asyncio.sleep(0.6)
            yield RunEvent(
                type="step_end",
                data={
                    "tool": "orders_list",
                    "status": "ok",
                    "output": {
                        "total": 4,
                        "data": [
                            {"po_id": "PO2026001", "supplier_id": "S001", "amount": 35000, "status": "已发货"},
                            {"po_id": "PO2026002", "supplier_id": "S002", "amount": 5000, "status": "已完成"},
                        ]
                    }
                },
                iteration=0,
                step=4,
            )

        elif any(kw in msg_lower for kw in ["需求", "排名", "top"]):
            await asyncio.sleep(0.8)
            yield RunEvent(
                type="step_start",
                data={
                    "tool": "top_materials",
                    "action": "analytics/top_materials_by_demand",
                    "args": {"date_from": "2026-01-01", "date_to": "2026-05-14", "top_n": 5},
                },
                iteration=0,
                step=3,
            )

            await asyncio.sleep(0.6)
            yield RunEvent(
                type="step_end",
                data={
                    "tool": "top_materials",
                    "status": "ok",
                    "output": {
                        "date_from": "2026-01-01",
                        "date_to": "2026-05-14",
                        "data": [
                            {"rank": 1, "material_id": "M001", "material_name": "钢板", "total_demand": 500, "unit": "吨"},
                            {"rank": 2, "material_id": "M002", "material_name": "螺丝", "total_demand": 20000, "unit": "个"},
                            {"rank": 3, "material_id": "M004", "material_name": "电线", "total_demand": 3000, "unit": "米"},
                        ]
                    }
                },
                iteration=0,
                step=4,
            )

        else:
            # 默认回复
            await asyncio.sleep(0.8)
            yield RunEvent(
                type="prelude_delta",
                data={"content": "我收到了您的消息。让我为您查询相关信息..."},
                iteration=0,
                step=3,
            )
            await asyncio.sleep(0.5)

        # 最终回复
        await asyncio.sleep(0.3)
        yield RunEvent(
            type="final_delta",
            data={
                "content": self._generate_response(user_message, intent_result)
            },
            iteration=0,
            step=5,
        )

        yield RunEvent(
            type="done",
            data={"timestamp": self._get_timestamp()},
            iteration=0,
            step=6,
        )

    def _generate_response(self, user_message: str, intent_result) -> str:
        """生成 Mock 响应"""
        msg_lower = user_message.lower()

        if any(kw in msg_lower for kw in ["物料", "材料", "查询所有"]):
            return """根据查询结果，以下是物料列表：

| 物料编码 | 物料名称 | 单位 |
|---------|---------|------|
| M001 | 钢板 | 吨 |
| M002 | 螺丝 | 个 |
| M003 | 电机 | 台 |
| M004 | 电线 | 米 |
| M005 | 润滑油 | 桶 |

如需了解某个物料的详细信息，请告诉我物料编码。"""

        elif "供应商" in msg_lower:
            return """以下是供应商列表：

| 供应商编码 | 供应商名称 | 联系人 |
|-----------|-----------|--------|
| S001 | 华东钢材公司 | 张经理 |
| S002 | 精密螺丝厂 | 李经理 |
| S003 | 电机科技有限公司 | 王经理 |
| S004 | 五金贸易公司 | 赵经理 |

需要查看供应商的详细绩效数据吗？"""

        elif any(kw in msg_lower for kw in ["订单", "po"]):
            return """以下是最近的采购订单：

| 订单号 | 供应商 | 金额 | 状态 |
|--------|--------|------|------|
| PO2026001 | 华东钢材公司 | ¥35,000 | 已发货 |
| PO2026002 | 精密螺丝厂 | ¥5,000 | 已完成 |
| PO2026003 | 电机科技 | ¥25,000 | 处理中 |

需要查看订单详情或其他筛选条件？"""

        elif any(kw in msg_lower for kw in ["需求", "排名", "top"]):
            return """以下是需求量 Top 3 物料：

| 排名 | 物料编码 | 物料名称 | 总需求量 | 单位 |
|------|---------|---------|---------|------|
| 1 | M001 | 钢板 | 500 | 吨 |
| 2 | M002 | 螺丝 | 20,000 | 个 |
| 3 | M004 | 电线 | 3,000 | 米 |

数据范围：2026-01-01 至 2026-05-14"""

        elif any(greeting in msg_lower for greeting in ["hello", "你好", "hi", "您好", "嗨"]):
            return """您好！我是采购助手，可以帮您：

- **查询物料** - 查询物料主数据和库存
- **查询供应商** - 查看供应商信息
- **查询订单** - 追踪采购订单状态
- **数据分析** - 需求排名、供应商绩效分析

请问有什么可以帮您？"""

        else:
            return f"""我理解了，您说的是「{user_message}」。

作为采购助手，我可以帮您：

1. **物料管理** - 查询物料主数据、库存信息
2. **供应商管理** - 查看供应商信息和绩效
3. **订单追踪** - 查询采购订单状态
4. **数据分析** - 需求排名、供应商绩效分析

请告诉我您的需求。"""

    # ========== 采购审批工作流 ==========

    def _is_procurement_workflow(self, message: str) -> bool:
        """检测是否为采购审批工作流场景"""
        keywords = [
            "采购申请", "申请单", "待审批", "审批",
            "PR", "procurement", "approval"
        ]
        return any(kw in message.lower() for kw in keywords)

    async def _run_procurement_workflow(self, user_message: str) -> AsyncGenerator[RunEvent, None]:
        """
        运行采购审批工作流

        工作流程:
        1. 日期转换（内部函数，减少 LLM token）
        2. 意图识别
        3. 任务规划
        4. 分步执行
        5. 自动审批 / 等待 HITL
        """
        # Step 1: 基础技能 - 日期转换（内部函数）
        yield RunEvent(
            type="skill_call",
            data={
                "skill": "date_converter",
                "skill_name": "日期转换（内部函数）",
                "description": "将自然语言日期转换为精确日期",
                "internal": True,  # 标记为内部函数
            },
            iteration=0,
            step=1,
        )

        # 解析日期（使用内部函数，不消耗 LLM token）
        date_range = self.workflow_engine.convert_date_reference(user_message)

        yield RunEvent(
            type="skill_result",
            data={
                "skill": "date_converter",
                "result": {
                    "date_from": date_range.start,
                    "date_to": date_range.end,
                    "is_today": date_range.is_today,
                    "note": "使用内部函数解析，无需 LLM 参与",
                }
            },
            iteration=0,
            step=2,
        )

        # Step 2: 意图识别
        yield RunEvent(
            type="thinking",
            data={"thought": "正在识别用户意图..."},
            iteration=0,
            step=3,
        )

        intent_result = self.workflow_engine.recognize_intent(user_message)

        yield RunEvent(
            type="intent",
            data={
                "type": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "entities": intent_result["entities"],
                "suggested_actions": intent_result["suggested_actions"],
            },
            iteration=0,
            step=4,
        )

        # Step 3: 任务规划
        yield RunEvent(
            type="thinking",
            data={"thought": "正在生成执行计划..."},
            iteration=0,
            step=5,
        )

        workflow_plan = self.workflow_engine.plan_workflow(intent_result, user_message)

        yield RunEvent(
            type="plan",
            data={
                "tasks": [t.to_dict() for t in workflow_plan.tasks],
                "auto_approve_threshold": workflow_plan.auto_approve_threshold,
            },
            iteration=0,
            step=6,
        )

        # Step 4: 执行任务 - 查询待审批申请
        yield RunEvent(
            type="thinking",
            data={"thought": "正在查询采购申请单..."},
            iteration=0,
            step=7,
        )

        # 执行查询任务
        query_task = workflow_plan.tasks[0]
        requests = await self.workflow_engine.execute_task(query_task)

        yield RunEvent(
            type="step_start",
            data={
                "tool": "query_procurement_requests",
                "action": "procurement_requests/list",
                "args": query_task.params,
            },
            iteration=0,
            step=8,
        )

        yield RunEvent(
            type="step_end",
            data={
                "tool": "query_procurement_requests",
                "status": "ok",
                "output": {
                    "total": len(requests),
                    "data": requests,
                }
            },
            iteration=0,
            step=9,
        )

        # Step 5: 分析并分类申请
        yield RunEvent(
            type="thinking",
            data={"thought": "正在分析申请单，确定审批方式..."},
            iteration=0,
            step=10,
        )

        analysis = self.workflow_engine.analyze_requests(requests)

        yield RunEvent(
            type="analysis",
            data={
                "auto_approve": analysis["auto_approve"],
                "hitl_approve": analysis["hitl_approve"],
                "summary": analysis["summary"],
            },
            iteration=0,
            step=11,
        )

        # Step 6: 执行自动审批
        auto_results = []
        for req in analysis["auto_approve"]:
            result = self.workflow_engine.auto_approve(req)
            auto_results.append(result)

            yield RunEvent(
                type="auto_approved",
                data=result,
                iteration=0,
                step=12,
            )

        # Step 7: 准备 HITL 审批
        hitl_requests = []
        for req in analysis["hitl_approve"]:
            hitl_data = self.workflow_engine.prepare_hitl_approval(req)
            hitl_requests.append(hitl_data)

            yield RunEvent(
                type="hitl_pending",
                data=hitl_data,
                iteration=0,
                step=13,
            )

        # Step 8: 生成最终响应
        yield RunEvent(
            type="final_delta",
            data={
                "content": self._generate_procurement_response(
                    date_range=date_range,
                    analysis=analysis,
                    auto_results=auto_results,
                    hitl_requests=hitl_requests,
                )
            },
            iteration=0,
            step=14,
        )

        yield RunEvent(
            type="done",
            data={"timestamp": self._get_timestamp()},
            iteration=0,
            step=15,
        )

    def _generate_procurement_response(
        self,
        date_range,
        analysis: Dict,
        auto_results: List[Dict],
        hitl_requests: List[Dict],
    ) -> str:
        """生成采购审批工作流的响应"""
        summary = analysis["summary"]

        lines = [
            f"## 查询结果",
            "",
            f"**日期范围**: {date_range.start} 至 {date_range.end}",
            f"**待审批总数**: {summary['auto_count'] + summary['hitl_count']} 单",
            "",
        ]

        # 自动审批结果
        if auto_results:
            lines.extend([
                "### 自动审批（金额 ≤ 1000 元）",
                "",
                f"已自动审批 **{len(auto_results)}** 单，金额合计 **¥{summary['auto_total']:.2f}**",
                "",
                "| 申请单号 | 申请人 | 部门 | 金额 | 状态 |",
                "|---------|-------|------|------|------|",
            ])

            for result in auto_results:
                req = next(r for r in analysis["auto_approve"] if r["request_no"] == result["request_no"])
                lines.append(f"| {result['request_no']} | {req.get('applicant', '-')} | {req.get('department', '-')} | ¥{req.get('amount', 0):.2f} | ✅ 自动通过 |")

            lines.append("")

        # HITL 审批
        if hitl_requests:
            lines.extend([
                "### 需要人工审批（金额 > 1000 元）",
                "",
                f"需要您审批 **{len(hitl_requests)}** 单，金额合计 **¥{summary['hitl_total']:.2f}**",
                "",
                "| 申请单号 | 申请人 | 部门 | 金额 | 申请标题 |",
                "|---------|-------|------|------|---------|",
            ])

            for req in hitl_requests:
                lines.append(
                    f"| {req['request_no']} | {req['requester']['name']} | {req['requester']['department']} | "
                    f"**¥{req['amount']:.2f}** | {req['title']} |"
                )

            lines.extend([
                "",
                "---",
                "",
                "**请选择审批操作**:",
                "- 回复 `审批通过 PR-xxx` 来批准某张申请",
                "- 回复 `审批拒绝 PR-xxx` 并说明理由来拒绝",
                "- 回复 `全部通过` 来批准以上所有申请",
            ])

        if not hitl_requests and auto_results:
            lines.extend([
                "---",
                "",
                "✅ **所有待审批申请已处理完毕！**",
            ])

        return "\n".join(lines)

    def abort(self):
        """中止运行"""
        self._should_abort = True

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
