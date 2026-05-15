"""
连接器 (Connector) 数据模型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Awaitable
import httpx
import json


@dataclass
class ConnectorAction:
    """连接器提供的 Action"""
    id: str
    name: str
    description: str
    endpoint: str
    method: str = "POST"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    mock_response: Optional[Dict[str, Any]] = None


@dataclass
class ConnectorConfig:
    """连接器配置"""
    id: str
    name: str
    description: str
    category: str = "builtin"  # builtin, materials, procurement, analytics, gateway
    enabled: bool = True
    base_url: str = ""
    auth: Dict[str, str] = field(default_factory=dict)
    actions: List[ConnectorAction] = field(default_factory=list)
    is_mock: bool = True  # 是否为 mock 模式


class MockConnector:
    """
    Mock 连接器 - 用于演示
    提供模拟的物料、供应商、订单数据
    """

    def __init__(self):
        self.config = ConnectorConfig(
            id="mock-procurement",
            name="采购系统 (Mock)",
            description="演示用采购系统连接器",
            category="procurement",
            enabled=True,
            is_mock=True,
            actions=self._build_actions(),
        )

    def _build_actions(self) -> List[ConnectorAction]:
        return [
            ConnectorAction(
                id="materials/list",
                name="查询物料列表",
                description="分页查询物料主数据",
                endpoint="/oracle/materials",
                method="GET",
                mock_response=self._mock_materials(),
            ),
            ConnectorAction(
                id="materials/get_by_id",
                name="获取物料详情",
                description="根据物料编码获取详细信息",
                endpoint="/oracle/materials/{material_id}",
                method="GET",
                mock_response=self._mock_material_detail(),
            ),
            ConnectorAction(
                id="suppliers/list",
                name="查询供应商列表",
                description="分页查询供应商主数据",
                endpoint="/sap/suppliers",
                method="GET",
                mock_response=self._mock_suppliers(),
            ),
            ConnectorAction(
                id="purchase_orders/list",
                name="查询采购订单",
                description="分页查询采购订单",
                endpoint="/dtp/purchase_orders/list",
                method="POST",
                mock_response=self._mock_orders(),
            ),
            ConnectorAction(
                id="analytics/top_materials_by_demand",
                name="需求排名物料",
                description="按需求计划数量排名Top物料",
                endpoint="/sap/analytics/top_materials",
                method="POST",
                mock_response=self._mock_top_materials(),
            ),
            ConnectorAction(
                id="analytics/supplier_performance",
                name="供应商绩效",
                description="分析供应商交付绩效",
                endpoint="/sap/analytics/supplier_perf",
                method="POST",
                mock_response=self._mock_supplier_perf(),
            ),
        ]

    def _mock_materials(self) -> Dict[str, Any]:
        return {
            "total": 5,
            "page": 1,
            "page_size": 20,
            "data": [
                {"material_id": "M001", "material_name": "钢板", "unit": "吨", "plant_id": "P100"},
                {"material_id": "M002", "material_name": "螺丝", "unit": "个", "plant_id": "P100"},
                {"material_id": "M003", "material_name": "电机", "unit": "台", "plant_id": "P100"},
                {"material_id": "M004", "material_name": "电线", "unit": "米", "plant_id": "P100"},
                {"material_id": "M005", "material_name": "润滑油", "unit": "桶", "plant_id": "P100"},
            ]
        }

    def _mock_material_detail(self) -> Dict[str, Any]:
        return {
            "material_id": "M001",
            "material_name": "钢板",
            "unit": "吨",
            "plant_id": "P100",
            "plant_name": "北京工厂",
            "stock": 150.5,
            "safety_stock": 50.0,
            "standard_cost": 3500.0,
            "supplier": "S001",
        }

    def _mock_suppliers(self) -> Dict[str, Any]:
        return {
            "total": 4,
            "data": [
                {"supplier_id": "S001", "supplier_name": "华东钢材公司", "contact": "张经理", "tel": "021-12345678"},
                {"supplier_id": "S002", "supplier_name": "精密螺丝厂", "contact": "李经理", "tel": "0755-87654321"},
                {"supplier_id": "S003", "supplier_name": "电机科技有限公司", "contact": "王经理", "tel": "010-11223344"},
                {"supplier_id": "S004", "supplier_name": "五金贸易公司", "contact": "赵经理", "tel": "020-55667788"},
            ]
        }

    def _mock_orders(self) -> Dict[str, Any]:
        return {
            "total": 8,
            "data": [
                {"po_id": "PO2026001", "supplier_id": "S001", "material_id": "M001", "quantity": 10, "amount": 35000, "status": "已发货", "create_date": "2026-05-10"},
                {"po_id": "PO2026002", "supplier_id": "S002", "material_id": "M002", "quantity": 5000, "amount": 5000, "status": "已完成", "create_date": "2026-05-08"},
                {"po_id": "PO2026003", "supplier_id": "S003", "material_id": "M003", "quantity": 5, "amount": 25000, "status": "处理中", "create_date": "2026-05-12"},
                {"po_id": "PO2026004", "supplier_id": "S001", "material_id": "M001", "quantity": 20, "amount": 70000, "status": "已发货", "create_date": "2026-05-11"},
            ]
        }

    def _mock_top_materials(self) -> Dict[str, Any]:
        return {
            "date_from": "2026-01-01",
            "date_to": "2026-05-14",
            "top_n": 10,
            "data": [
                {"rank": 1, "material_id": "M001", "material_name": "钢板", "total_demand": 500, "unit": "吨"},
                {"rank": 2, "material_id": "M002", "material_name": "螺丝", "total_demand": 20000, "unit": "个"},
                {"rank": 3, "material_id": "M004", "material_name": "电线", "total_demand": 3000, "unit": "米"},
            ]
        }

    def _mock_supplier_perf(self) -> Dict[str, Any]:
        return {
            "date_from": "2026-01-01",
            "date_to": "2026-05-14",
            "data": [
                {"supplier_id": "S001", "supplier_name": "华东钢材公司", "total_orders": 15, "on_time_count": 14, "on_time_rate": 93.3, "avg_lead_time": 5.2},
                {"supplier_id": "S002", "supplier_name": "精密螺丝厂", "total_orders": 20, "on_time_count": 19, "on_time_rate": 95.0, "avg_lead_time": 3.1},
                {"supplier_id": "S003", "supplier_name": "电机科技有限公司", "total_orders": 8, "on_time_count": 6, "on_time_rate": 75.0, "avg_lead_time": 10.5},
            ]
        }

    async def execute(self, action_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Action"""
        for action in self.config.actions:
            if action.id == action_id:
                # 应用参数替换
                endpoint = action.endpoint
                for key, value in params.items():
                    endpoint = endpoint.replace(f"{{{key}}}", str(value))

                # 返回 mock 响应
                return {
                    "success": True,
                    "action": action_id,
                    "endpoint": endpoint,
                    "params": params,
                    "data": action.mock_response or {},
                }

        return {
            "success": False,
            "error": f"Action not found: {action_id}",
        }


class ConnectorRegistry:
    """连接器注册表"""

    def __init__(self):
        self._connectors: Dict[str, ConnectorConfig] = {}
        self._mock = MockConnector()
        self._register_mock()

    def _register_mock(self):
        self._connectors[self._mock.config.id] = self._mock.config

    def register(self, connector: ConnectorConfig):
        self._connectors[connector.id] = connector

    def get(self, connector_id: str) -> Optional[ConnectorConfig]:
        return self._connectors.get(connector_id)

    def list_all(self) -> List[ConnectorConfig]:
        return list(self._connectors.values())

    def list_enabled(self) -> List[ConnectorConfig]:
        return [c for c in self._connectors.values() if c.enabled]

    def get_action(self, action_id: str) -> Optional[ConnectorAction]:
        for connector in self._connectors.values():
            for action in connector.actions:
                if action.id == action_id:
                    return action
        return None

    def get_mock_connector(self) -> MockConnector:
        return self._mock
