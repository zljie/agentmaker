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
            model = OpenAIChatModel(
                model_name=self.model_config.get("model_name", "gpt-4o"),
                api_key=api_key,
                api_base=self.model_config.get("api_base", "https://api.openai.com/v1"),
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

    def abort(self):
        """中止运行"""
        self._should_abort = True

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
