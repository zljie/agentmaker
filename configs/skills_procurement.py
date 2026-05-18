"""
采购审批技能定义
"""

PROCUREMENT_SKILLS = """
skills:
  # ========== 基础技能：日期转换 ==========
  - id: skill/date_converter
    name: 日期转换（内部函数）
    description: 将自然语言日期转换为精确日期范围，用于减少 LLM token 消耗
    kind: utility
    operation: convert
    labels: [utility, date, internal]
    enabled: true
    priority: 100  # 最高优先级，基础技能

  # ========== 查询技能 ==========
  - id: skill/query_procurement_requests
    name: 查询采购申请单
    description: 查询采购申请单列表，支持按日期、状态、金额等条件筛选
    action_id: procurement_requests/list
    tool: query_procurement_requests
    kind: query
    operation: list
    entity_name: procurement_requests
    labels: [query, procurement]
    enabled: true
    priority: 80
    input_schema:
      type: object
      properties:
        date_from:
          type: string
          format: date
          description: 开始日期（ISO格式）
        date_to:
          type: string
          format: date
          description: 结束日期（ISO格式）
        status:
          type: string
          enum: [pending, approved, rejected, all]
          default: pending
          description: 申请状态
        amount_operator:
          type: string
          enum: [gt, lt, gte, lte, eq]
          description: 金额比较操作符
        amount_value:
          type: number
          description: 金额值
        page:
          type: integer
          default: 1
        page_size:
          type: integer
          default: 20

  # ========== 审批技能 ==========
  - id: skill/approve_procurement_request
    name: 审批采购申请
    description: 对采购申请单进行审批操作（同意或拒绝）
    action_id: procurement_requests/approve
    tool: approve_procurement_request
    kind: operation
    operation: approve
    entity_name: procurement_requests
    labels: [operation, approval]
    enabled: true
    priority: 70
    needs_hitl: true  # 大额申请需要人工审批
    input_schema:
      type: object
      required: [request_no, action]
      properties:
        request_no:
          type: string
          description: 申请单号
        action:
          type: string
          enum: [approve, reject]
          description: 审批动作
        comment:
          type: string
          description: 审批意见
    output_schema:
      type: object
      properties:
        success:
          type: boolean
        request_no:
          type: string
        action:
          type: string
        approved_at:
          type: string
          format: date-time

  # ========== 批量审批技能 ==========
  - id: skill/batch_approve_procurement
    name: 批量审批采购申请
    description: 对符合条件的采购申请单进行批量审批
    action_id: procurement_requests/batch_approve
    tool: batch_approve_procurement
    kind: operation
    operation: batch_approve
    entity_name: procurement_requests
    labels: [operation, batch]
    enabled: true
    priority: 65
    needs_hitl: true
    input_schema:
      type: object
      required: [action]
      properties:
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date
        amount_threshold:
          type: number
          description: 金额阈值
        action:
          type: string
          enum: [approve, reject]
          description: 审批动作

  # ========== 审批摘要技能 ==========
  - id: skill/approval_summary
    name: 审批摘要
    description: 获取待审批申请的统计摘要
    action_id: procurement_requests/summary
    tool: approval_summary
    kind: analytics
    operation: aggregate
    entity_name: procurement_requests
    labels: [analytics, summary]
    enabled: true
    priority: 60
    input_schema:
      type: object
      properties:
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date

  # ========== HITL 审批查询 ==========
  - id: skill/hitl_pending_approvals
    name: 待人工审批列表
    description: 获取需要人工审批的大额采购申请
    action_id: procurement_requests/hitl_pending
    tool: hitl_pending_approvals
    kind: query
    operation: list
    entity_name: procurement_requests
    labels: [query, hitl]
    enabled: true
    priority: 75
    input_schema:
      type: object
      properties:
        threshold:
          type: number
          description: 金额阈值（默认1000）
"""
