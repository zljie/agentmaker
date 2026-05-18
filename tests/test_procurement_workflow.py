"""
采购审批工作流测试脚本
"""
import asyncio
import json
from services.procurement_workflow import (
    ProcurementWorkflowEngine,
    DateRange,
    TaskType,
)


def test_date_conversion():
    """测试日期转换基础技能"""
    print("=" * 60)
    print("测试 1: 日期转换基础技能")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    test_cases = [
        "今天",
        "今日",
        "本周",
        "本月",
        "昨天",
        "上周",
    ]

    for text in test_cases:
        result = engine.convert_date_reference(text)
        print(f"  '{text}' -> {result.start} 至 {result.end} (is_today={result.is_today})")

    print()


def test_intent_recognition():
    """测试意图识别"""
    print("=" * 60)
    print("测试 2: 意图识别")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    test_cases = [
        "查询今日待审批的采购申请单",
        "查询金额大于1000的申请",
        "本周有哪些采购需要审批",
        "查看待审批的PR",
    ]

    for message in test_cases:
        result = engine.recognize_intent(message)
        print(f"\n  用户: {message}")
        print(f"  意图: {result['intent']} (置信度: {result['confidence']:.2f})")
        print(f"  实体: {json.dumps(result['entities'], ensure_ascii=False, indent=4)}")

    print()


def test_workflow_planning():
    """测试工作流规划"""
    print("=" * 60)
    print("测试 3: 工作流规划")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    message = "查询今日待审批的采购申请单，如果金额大于1000的需要人工审核"

    intent_result = engine.recognize_intent(message)
    print(f"  意图识别结果: {intent_result['intent']}")

    plan = engine.plan_workflow(intent_result, message)
    print(f"  生成任务数: {len(plan.tasks)}")

    for i, task in enumerate(plan.tasks, 1):
        print(f"    任务 {i}: {task.task_id} - {task.description}")
        print(f"      类型: {task.task_type.value}")
        print(f"      参数: {task.params}")

    print()


async def test_query_execution():
    """测试查询执行"""
    print("=" * 60)
    print("测试 4: 查询执行")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    # 执行查询任务
    task = engine.plan_workflow(
        engine.recognize_intent("查询今日待审批的采购申请单"),
        "查询今日待审批的采购申请单"
    ).tasks[0]

    results = await engine.execute_task(task)
    print(f"  查询到 {len(results)} 条待审批申请:")

    for req in results:
        print(f"\n    申请单号: {req['request_no']}")
        print(f"    申请人: {req['applicant']}")
        print(f"    部门: {req['department']}")
        print(f"    金额: ¥{req['amount']:.2f}")
        print(f"    需要人工审核: {'是' if req['needs_manual_review'] else '否'}")

    print()


def test_analysis():
    """测试申请分析"""
    print("=" * 60)
    print("测试 5: 申请分析与分类")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    # 模拟查询结果（包含 needs_manual_review 字段）
    requests = [
        {"request_no": "PR-001", "applicant": "张三", "amount": 500, "needs_manual_review": False, "items": []},
        {"request_no": "PR-002", "applicant": "李四", "amount": 3500, "needs_manual_review": True, "items": []},
        {"request_no": "PR-003", "applicant": "王五", "amount": 800, "needs_manual_review": False, "items": []},
        {"request_no": "PR-004", "applicant": "赵六", "amount": 15000, "needs_manual_review": True, "items": []},
    ]

    analysis = engine.analyze_requests(requests)

    print(f"  自动审批 ({analysis['summary']['auto_count']} 单):")
    for req in analysis["auto_approve"]:
        print(f"    - {req['request_no']}: ¥{req['amount']}")

    print(f"\n  需要人工审批 ({analysis['summary']['hitl_count']} 单):")
    for req in analysis["hitl_approve"]:
        print(f"    - {req['request_no']}: ¥{req['amount']}")

    print(f"\n  汇总:")
    print(f"    自动审批总额: ¥{analysis['summary']['auto_total']}")
    print(f"    人工审批总额: ¥{analysis['summary']['hitl_total']}")
    print(f"    审批阈值: ¥{analysis['summary']['threshold']}")

    print()


def test_approval():
    """测试审批操作"""
    print("=" * 60)
    print("测试 6: 审批操作")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()

    # 模拟 HITL 申请
    hitl_request = {
        "request_no": "PR-002",
        "title": "服务器升级",
        "applicant": "李四",
        "department": "运维部",
        "amount": 3500,
        "currency": "CNY",
        "description": "采购2台高性能服务器",
        "items": [],
    }

    # 准备 HITL
    hitl_data = engine.prepare_hitl_approval(hitl_request)
    print(f"  准备 HITL 审批:")
    print(f"    申请单号: {hitl_data['request_no']}")
    print(f"    金额: ¥{hitl_data['amount']}")
    print(f"    阈值说明: {hitl_data['threshold_note']}")

    # 提交审批
    result = engine.submit_approval("PR-002", "approve", "同意采购")
    print(f"\n  审批结果: {result}")

    print()


def test_full_workflow():
    """测试完整工作流"""
    print("=" * 60)
    print("测试 7: 完整工作流模拟")
    print("=" * 60)

    engine = ProcurementWorkflowEngine()
    user_message = "查询今日待审批的采购申请单，如果金额大于1000的需要人工审核"

    print(f"  用户输入: {user_message}")
    print()

    # Step 1: 日期转换（内部函数）
    print("  [Step 1] 日期转换（内部函数）")
    date_range = engine.convert_date_reference(user_message)
    print(f"        日期范围: {date_range.start} 至 {date_range.end}")
    print(f"        是否今日: {date_range.is_today}")
    print()

    # Step 2: 意图识别
    print("  [Step 2] 意图识别")
    intent_result = engine.recognize_intent(user_message)
    print(f"        意图类型: {intent_result['intent']}")
    print(f"        置信度: {intent_result['confidence']:.2f}")
    print()

    # Step 3: 任务规划
    print("  [Step 3] 任务规划")
    plan = engine.plan_workflow(intent_result, user_message)
    for i, task in enumerate(plan.tasks, 1):
        print(f"        任务 {i}: {task.description}")
    print()

    # Step 4: 执行查询
    print("  [Step 4] 执行查询")
    requests = engine._query_pending_requests(
        date_from=date_range.start,
        date_to=date_range.end,
        status="pending"
    )
    print(f"        查询到 {len(requests)} 条申请")
    print()

    # Step 5: 分析分类
    print("  [Step 5] 分析与分类")
    analysis = engine.analyze_requests(requests)
    print(f"        自动审批: {analysis['summary']['auto_count']} 单 (¥{analysis['summary']['auto_total']})")
    print(f"        人工审批: {analysis['summary']['hitl_count']} 单 (¥{analysis['summary']['hitl_total']})")
    print()

    # Step 6: 执行自动审批
    print("  [Step 6] 执行自动审批")
    for req in analysis["auto_approve"]:
        result = engine.auto_approve(req)
        print(f"        ✅ {result['request_no']} - {result['action']}")

    # Step 7: 准备 HITL
    print()
    print("  [Step 7] 准备人工审批")
    for req in analysis["hitl_approve"]:
        hitl = engine.prepare_hitl_approval(req)
        print(f"        ⏳ {hitl['request_no']} - 金额 ¥{hitl['amount']} - {hitl['threshold_note']}")

    print()
    print("  [完成] 工作流执行完毕")
    print()


if __name__ == "__main__":
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "采购审批工作流测试套件" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # 执行所有测试
    test_date_conversion()
    test_intent_recognition()
    test_workflow_planning()
    asyncio.run(test_query_execution())
    test_analysis()
    test_approval()
    test_full_workflow()

    print()
    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
