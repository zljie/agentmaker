"""
采购审批工作流服务
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date
from enum import Enum
import json


class TaskType(Enum):
    """任务类型"""
    QUERY = "query"           # 查询任务
    APPROVE = "approve"        # 审批任务
    AUTO_APPROVE = "auto_approve"  # 自动审批
    HITL_APPROVE = "hitl_approve"   # 需要人工审批


class ApprovalAction(Enum):
    """审批动作"""
    APPROVE = "approve"        # 同意
    REJECT = "reject"          # 拒绝
    SKIP = "skip"              # 跳过


@dataclass
class DateRange:
    """日期范围"""
    start: str  # ISO 格式日期字符串
    end: str
    is_today: bool = False
    
    @classmethod
    def today(cls) -> "DateRange":
        """创建今日日期范围"""
        today_str = date.today().isoformat()
        return cls(start=today_str, end=today_str, is_today=True)
    
    @classmethod
    def parse(cls, text: str) -> "DateRange":
        """从自然语言解析日期范围"""
        today = date.today()
        
        text = text.lower().strip()
        
        if "今天" in text or "今日" in text or "today" in text:
            today_str = today.isoformat()
            return cls(start=today_str, end=today_str, is_today=True)
        
        elif "昨天" in text or "yesterday" in text:
            yesterday = today - __import__('datetime').timedelta(days=1)
            return cls(start=yesterday.isoformat(), end=yesterday.isoformat())
        
        elif "本周" in text or "this week" in text:
            # 本周一
            monday = today - __import__('datetime').timedelta(days=today.weekday())
            return cls(start=monday.isoformat(), end=today.isoformat())
        
        elif "本月" in text or "this month" in text:
            month_start = today.replace(day=1)
            return cls(start=month_start.isoformat(), end=today.isoformat())
        
        elif "上周" in text:
            monday = today - __import__('datetime').timedelta(days=today.weekday() + 7)
            sunday = monday + __import__('datetime').timedelta(days=6)
            return cls(start=monday.isoformat(), end=sunday.isoformat())
        
        else:
            # 默认返回今日
            return cls.today()


@dataclass
class ProcurementRequest:
    """采购申请单"""
    id: str
    request_no: str          # 申请单号
    title: str               # 申请标题
    applicant: str           # 申请人
    department: str          # 部门
    request_date: str        # 申请日期
    amount: float            # 申请金额
    currency: str = "CNY"   # 币种
    status: str = "pending"  # pending, approved, rejected
    description: str = ""     # 申请说明
    items: List[Dict] = field(default_factory=list)  # 采购明细
    
    def needs_manual_review(self, threshold: float = 1000) -> bool:
        """是否需要人工审核（金额大于阈值）"""
        return self.amount > threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_no": self.request_no,
            "title": self.title,
            "applicant": self.applicant,
            "department": self.department,
            "request_date": self.request_date,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "description": self.description,
            "needs_manual_review": self.needs_manual_review(),
            "items_count": len(self.items),
        }


@dataclass
class WorkflowTask:
    """工作流任务"""
    task_id: str
    task_type: TaskType
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    data: Any = None  # 关联的数据
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "params": self.params,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class WorkflowPlan:
    """工作流执行计划"""
    tasks: List[WorkflowTask] = field(default_factory=list)
    auto_approve_threshold: float = 1000.0  # 自动审批阈值
    
    def add_task(self, task: WorkflowTask):
        self.tasks.append(task)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_count": len(self.tasks),
            "auto_approve_threshold": self.auto_approve_threshold,
            "tasks": [t.to_dict() for t in self.tasks],
        }


class ProcurementWorkflowEngine:
    """
    采购审批工作流引擎
    
    工作流程:
    1. 日期解析（内部函数） -> 减少 LLM token 消耗
    2. 意图识别 -> 确定用户意图（查询、审批）
    3. 任务规划 -> 生成执行计划
    4. 分步执行 -> 执行每个任务
    5. HITL 处理 -> 对大额申请等待人工审批
    """
    
    def __init__(self, auto_approve_threshold: float = 1000.0):
        self.auto_approve_threshold = auto_approve_threshold
        
        # 模拟数据
        self._mock_requests = self._generate_mock_requests()
    
    def _generate_mock_requests(self) -> List[ProcurementRequest]:
        """生成模拟采购申请数据"""
        today = date.today().isoformat()
        
        return [
            ProcurementRequest(
                id="PR001",
                request_no="PR-2026-0518-001",
                title="办公电脑采购",
                applicant="张三",
                department="技术部",
                request_date=today,
                amount=850.00,
                status="pending",
                description="采购3台办公笔记本电脑",
                items=[
                    {"id": "PR001-L1", "item_name": "笔记本电脑", "quantity": 3, "unit": "台", "unit_price": 280.00, "amount": 840.00, "status": "pending"},
                    {"id": "PR001-L2", "item_name": "鼠标键盘套装", "quantity": 3, "unit": "套", "unit_price": 3.33, "amount": 10.00, "status": "pending"},
                ]
            ),
            ProcurementRequest(
                id="PR002",
                request_no="PR-2026-0518-002",
                title="服务器升级项目",
                applicant="李四",
                department="运维部",
                request_date=today,
                amount=35000.00,
                status="pending",
                description="采购2台高性能服务器",
                items=[
                    {"id": "PR002-L1", "item_name": "高性能服务器（主机）", "quantity": 2, "unit": "台", "unit_price": 15000.00, "amount": 30000.00, "status": "pending"},
                    {"id": "PR002-L2", "item_name": "服务器操作系统许可", "quantity": 2, "unit": "套", "unit_price": 2500.00, "amount": 5000.00, "status": "pending"},
                ]
            ),
            ProcurementRequest(
                id="PR003",
                request_no="PR-2026-0518-003",
                title="办公用品采购",
                applicant="王五",
                department="行政部",
                request_date=today,
                amount=560.50,
                status="pending",
                description="办公文具、打印耗材等",
                items=[
                    {"id": "PR003-L1", "item_name": "A4打印纸", "quantity": 10, "unit": "包", "unit_price": 25.00, "amount": 250.00, "status": "pending"},
                    {"id": "PR003-L2", "item_name": "彩色墨盒套装", "quantity": 5, "unit": "套", "unit_price": 62.10, "amount": 310.50, "status": "pending"},
                ]
            ),
            ProcurementRequest(
                id="PR004",
                request_no="PR-2026-0518-004",
                title="会议室设备更新",
                applicant="赵六",
                department="行政部门",
                request_date=today,
                amount=2800.00,
                status="pending",
                description="采购投影仪和音响设备",
                items=[
                    {"id": "PR004-L1", "item_name": "4K投影仪", "quantity": 1, "unit": "台", "unit_price": 2000.00, "amount": 2000.00, "status": "pending"},
                    {"id": "PR004-L2", "item_name": "会议音响系统", "quantity": 1, "unit": "套", "unit_price": 800.00, "amount": 800.00, "status": "pending"},
                ]
            ),
        ]
    
    # ========== 基础技能：日期转换 ==========
    
    def convert_date_reference(self, text: str) -> DateRange:
        """
        内部函数：将自然语言日期转换为精确日期范围
        这是基础技能，不消耗 LLM token
        
        Args:
            text: 日期描述文本（如"今天"、"本周"、"本月"）
            
        Returns:
            DateRange 对象，包含精确的起始和结束日期
        """
        return DateRange.parse(text)
    
    # ========== 意图识别 ==========
    
    def recognize_intent(self, message: str) -> Dict[str, Any]:
        """
        意图识别：分析用户消息，确定意图
        
        Returns:
            {
                "intent": str,           # 意图类型
                "entities": {},          # 提取的实体
                "confidence": float,     # 置信度
                "suggested_actions": []  # 建议的操作
            }
        """
        message_lower = message.lower()
        
        # 检测审批相关意图
        approval_keywords = ["审批", "审核", "批准", "通过", "review", "approve", "check"]
        query_keywords = ["查询", "查看", "列出", "今天", "待", "query", "list"]
        
        has_approval = any(kw in message_lower for kw in approval_keywords)
        has_query = any(kw in message_lower for kw in query_keywords)
        
        # 提取日期实体
        date_range = self.convert_date_reference(message)
        
        # 提取金额条件
        amount_threshold = None
        if "大于" in message or "超过" in message or ">1000" in message:
            amount_threshold = 1000
        
        entities = {
            "date_range": {
                "start": date_range.start,
                "end": date_range.end,
                "is_today": date_range.is_today,
            }
        }
        
        if amount_threshold:
            entities["amount_condition"] = {
                "operator": ">",
                "value": amount_threshold,
            }
        
        # 确定意图
        if has_approval and has_query:
            return {
                "intent": "query_pending_approvals",
                "entities": entities,
                "confidence": 0.95,
                "suggested_actions": ["query_requests", "plan_approval"],
            }
        elif has_query:
            return {
                "intent": "query_requests",
                "entities": entities,
                "confidence": 0.85,
                "suggested_actions": ["query_requests"],
            }
        elif has_approval:
            return {
                "intent": "approval_workflow",
                "entities": entities,
                "confidence": 0.80,
                "suggested_actions": ["plan_approval"],
            }
        
        return {
            "intent": "unknown",
            "entities": entities,
            "confidence": 0.30,
            "suggested_actions": [],
        }
    
    # ========== 任务规划 ==========
    
    def plan_workflow(self, intent_result: Dict, user_message: str) -> WorkflowPlan:
        """
        任务规划：根据意图生成执行计划
        
        Args:
            intent_result: 意图识别结果
            user_message: 原始用户消息
            
        Returns:
            WorkflowPlan 执行计划
        """
        plan = WorkflowPlan(auto_approve_threshold=self.auto_approve_threshold)
        
        intent = intent_result.get("intent", "")
        entities = intent_result.get("entities", {})
        date_range = entities.get("date_range", {})
        
        # 任务1: 查询今日待审批申请
        query_task = WorkflowTask(
            task_id="task_query_pending",
            task_type=TaskType.QUERY,
            description=f"查询 {date_range.get('start')} 的待审批采购申请单",
            params={
                "date_from": date_range.get("start"),
                "date_to": date_range.get("end"),
                "status": "pending",
            }
        )
        plan.add_task(query_task)
        
        # 任务2: 分析并分类申请（自动审批 vs 人工审批）
        analyze_task = WorkflowTask(
            task_id="task_analyze_and_classify",
            task_type=TaskType.QUERY,
            description="分析申请单金额，确定审批方式",
            params={
                "auto_threshold": self.auto_approve_threshold,
            }
        )
        plan.add_task(analyze_task)
        
        return plan
    
    # ========== 任务执行 ==========
    
    async def execute_task(self, task: WorkflowTask) -> Any:
        """
        执行单个任务
        
        Args:
            task: 工作流任务
            
        Returns:
            任务执行结果
        """
        if task.task_type == TaskType.QUERY:
            if task.task_id == "task_query_pending":
                return self._query_pending_requests(
                    date_from=task.params.get("date_from"),
                    date_to=task.params.get("date_to"),
                    status=task.params.get("status", "pending")
                )
        
        return {"error": f"Unknown task: {task.task_id}"}
    
    def _query_pending_requests(
        self,
        date_from: str,
        date_to: str,
        status: str = "pending"
    ) -> List[Dict]:
        """查询待审批申请单"""
        results = []
        
        for req in self._mock_requests:
            # 检查日期
            if not (date_from <= req.request_date <= date_to):
                continue
            
            # 检查状态
            if status and req.status != status:
                continue
            
            req_dict = req.to_dict()
            req_dict["items"] = req.items
            results.append(req_dict)
        
        return results
    
    def analyze_requests(self, requests: List[Dict]) -> Dict[str, Any]:
        """
        分析申请单，决定审批方式
        
        Returns:
            {
                "auto_approve": [...],  # 可自动审批的申请
                "hitl_approve": [...], # 需要人工审批的申请
                "summary": {...}       # 汇总信息
            }
        """
        auto_approve = []
        hitl_approve = []
        
        for req in requests:
            if req.get("needs_manual_review", False):
                hitl_approve.append(req)
            else:
                auto_approve.append(req)
        
        auto_total = sum(r.get("amount", 0) for r in auto_approve)
        hitl_total = sum(r.get("amount", 0) for r in hitl_approve)
        
        return {
            "auto_approve": auto_approve,
            "hitl_approve": hitl_approve,
            "summary": {
                "auto_count": len(auto_approve),
                "hitl_count": len(hitl_approve),
                "auto_total": auto_total,
                "hitl_total": hitl_total,
                "threshold": self.auto_approve_threshold,
            }
        }
    
    def auto_approve(self, request: Dict) -> Dict:
        """自动审批（小额申请）"""
        return {
            "request_no": request.get("request_no"),
            "action": "auto_approved",
            "approved_at": datetime.now().isoformat(),
            "approved_by": "system",
            "comment": f"金额 {request.get('amount')} 元低于阈值 {self.auto_approve_threshold} 元，自动审批通过",
        }
    
    def prepare_hitl_approval(self, request: Dict) -> Dict:
        """
        准备人工审批 - 基于明细行级别
        
        为每个明细行生成独立的审批项，支持企业级细粒度审批
        """
        # 为每个明细行生成审批项
        line_items = []
        for idx, item in enumerate(request.get("items", [])):
            line_item = {
                "line_no": idx + 1,
                "item_id": item.get("id", f"{request.get('request_no')}-L{idx+1}"),
                "item_name": item.get("item_name") or item.get("item", "未命名"),
                "quantity": item.get("quantity", 0),
                "unit": item.get("unit", ""),
                "unit_price": item.get("unit_price", 0),
                "line_amount": item.get("amount", 0),
                "status": "pending",  # pending, approved, rejected
            }
            line_items.append(line_item)

        # 如果没有明细行，创建一个汇总行
        if not line_items:
            line_items.append({
                "line_no": 1,
                "item_id": f"{request.get('request_no')}-SUMMARY",
                "item_name": request.get("title", "采购申请"),
                "quantity": 1,
                "unit": "项",
                "unit_price": request.get("amount", 0),
                "line_amount": request.get("amount", 0),
                "status": "pending",
            })

        return {
            "request_no": request.get("request_no"),
            "action": "pending_hitl",
            "status": "awaiting_approval",
            "requester": {
                "name": request.get("applicant"),
                "department": request.get("department"),
            },
            "amount": request.get("amount"),
            "currency": request.get("currency", "CNY"),
            "title": request.get("title"),
            "description": request.get("description"),
            "request_date": request.get("request_date"),
            # 明细行级别审批
            "line_items": line_items,
            "total_lines": len(line_items),
            "pending_lines": len([l for l in line_items if l["status"] == "pending"]),
            "threshold_note": f"金额 {request.get('amount')} 元超过阈值 {self.auto_approve_threshold} 元，需要人工审批",
        }

    def approve_line_item(
        self,
        request_no: str,
        line_id: str,
        action: str,
        comment: str = ""
    ) -> Dict:
        """
        审批单个明细行
        
        Args:
            request_no: 申请单号
            line_id: 明细行ID
            action: approve/reject
            comment: 审批意见
        """
        # 找到申请单
        request = None
        for req in self._mock_requests:
            if req.request_no == request_no:
                request = req
                break

        if not request:
            return {"success": False, "error": f"申请单 {request_no} 不存在"}

        # 更新明细行状态
        for item in request.items:
            item_id = item.get("id", "")
            if item_id == line_id or f"{request_no}-L{len(request.items)}" == line_id:
                item["status"] = "approved" if action == "approve" else "rejected"
                break

        # 检查是否所有行都已审批
        all_approved = all(
            item.get("status") in ["approved", "rejected"]
            for item in request.items
        )

        if all_approved:
            # 检查是否有拒绝的行
            has_rejected = any(item.get("status") == "rejected" for item in request.items)
            request.status = "rejected" if has_rejected else "approved"

        return {
            "success": True,
            "request_no": request_no,
            "line_id": line_id,
            "action": action,
            "comment": comment,
            "approved_at": datetime.now().isoformat(),
            "all_completed": all_approved,
            "request_status": request.status,
        }

    def get_request_with_lines(self, request_no: str) -> Optional[Dict]:
        """获取申请单及其明细行状态"""
        for req in self._mock_requests:
            if req.request_no == request_no:
                data = req.to_dict()
                data["items"] = req.items
                return data
        return None
    
    def submit_approval(self, request_no: str, action: str, comment: str = "") -> Dict:
        """
        提交审批结果
        
        Args:
            request_no: 申请单号
            action: approve/reject
            comment: 审批意见
            
        Returns:
            审批结果
        """
        if action == ApprovalAction.APPROVE.value:
            # 找到并更新申请状态
            for req in self._mock_requests:
                if req.request_no == request_no:
                    req.status = "approved"
                    break
            
            return {
                "success": True,
                "request_no": request_no,
                "action": "approved",
                "approved_at": datetime.now().isoformat(),
                "comment": comment or "审批通过",
            }
        
        elif action == ApprovalAction.REJECT.value:
            for req in self._mock_requests:
                if req.request_no == request_no:
                    req.status = "rejected"
                    break
            
            return {
                "success": True,
                "request_no": request_no,
                "action": "rejected",
                "rejected_at": datetime.now().isoformat(),
                "comment": comment or "审批拒绝",
            }
        
        return {
            "success": False,
            "error": f"Invalid action: {action}",
        }


# 全局工作流引擎实例
_workflow_engine: Optional[ProcurementWorkflowEngine] = None


def get_workflow_engine() -> ProcurementWorkflowEngine:
    """获取工作流引擎实例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = ProcurementWorkflowEngine(auto_approve_threshold=1000.0)
    return _workflow_engine
