"""
采购审批本体 (Ontology)
定义采购申请单相关的实体和操作
"""

PROCUREMENT_ONTOLOGY = """
domain: procurement_approval
version: 1.0.0
description: 采购审批管理系统本体

entities:
  # ========== 采购申请单 ==========
  procurement_requests:
    description: 采购申请单，记录员工发起的采购需求
    labels: [core_entity, transactional]
    dataset: procurement_requests
    properties:
      - name: id
        type: string
        description: 申请单ID
        required: true
      - name: request_no
        type: string
        description: 申请单编号 (如 PR-2026-0518-001)
        required: true
      - name: title
        type: string
        description: 申请标题
        required: true
      - name: applicant
        type: string
        description: 申请人姓名
        required: true
      - name: department
        type: string
        description: 申请人所属部门
        required: true
      - name: request_date
        type: string
        format: date
        description: 申请日期
        required: true
      - name: amount
        type: number
        description: 申请总金额
        required: true
      - name: currency
        type: string
        description: 币种，默认 CNY
        default: CNY
      - name: status
        type: string
        description: 申请状态 (pending/approved/rejected)
        default: pending
      - name: description
        type: string
        description: 申请说明
      - name: created_at
        type: string
        format: datetime
        description: 创建时间

  # ========== 采购明细 ==========
  procurement_items:
    description: 采购申请明细行
    labels: [detail]
    dataset: procurement_items
    properties:
      - name: id
        type: string
        description: 明细行ID
        required: true
      - name: request_id
        type: string
        description: 关联的申请单ID
        required: true
      - name: item_name
        type: string
        description: 物品名称
        required: true
      - name: quantity
        type: number
        description: 采购数量
        required: true
      - name: unit
        type: string
        description: 单位
      - name: unit_price
        type: number
        description: 单价
        required: true
      - name: amount
        type: number
        description: 小计金额
        required: true

  # ========== 审批记录 ==========
  approval_records:
    description: 审批操作记录
    labels: [audit]
    dataset: approval_records
    properties:
      - name: id
        type: string
        description: 审批记录ID
        required: true
      - name: request_no
        type: string
        description: 关联的申请单号
        required: true
      - name: action
        type: string
        description: 审批动作 (approve/reject)
        required: true
      - name: approver
        type: string
        description: 审批人
        required: true
      - name: approver_type
        type: string
        description: 审批类型 (auto/manual)
        required: true
      - name: comment
        type: string
        description: 审批意见
      - name: approved_at
        type: string
        format: datetime
        description: 审批时间
        required: true

actions:
  # ========== 查询操作 ==========
  - id: procurement_requests/list
    name: 查询采购申请单列表
    description: 分页查询采购申请单，支持按日期、状态、金额等条件筛选
    kind: query
    operation: list
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [query]
    input_schema:
      type: object
      properties:
        date_from:
          type: string
          format: date
          description: 开始日期
        date_to:
          type: string
          format: date
          description: 结束日期
        status:
          type: string
          enum: [pending, approved, rejected, all]
          default: pending
          description: 申请状态
        amount_operator:
          type: string
          enum: [gt, lt, gte, lte, eq]
          description: 金额比较操作符 (gt大于/lt小于/gte大于等于/lte小于等于/eq等于)
        amount_value:
          type: number
          description: 金额值
        page:
          type: integer
          default: 1
        page_size:
          type: integer
          default: 20

  - id: procurement_requests/get_by_id
    name: 获取采购申请单详情
    description: 根据申请单号获取完整的申请信息，包括明细行
    kind: query
    operation: get
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [query]
    input_schema:
      type: object
      required: [request_no]
      properties:
        request_no:
          type: string
          description: 申请单号

  - id: procurement_requests/query_pending
    name: 查询待审批申请
    description: 快捷查询待审批的采购申请单
    kind: query
    operation: list
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [query, workflow]
    input_schema:
      type: object
      properties:
        date_from:
          type: string
          format: date
          description: 开始日期
        date_to:
          type: string
          format: date
          description: 结束日期

  - id: procurement_requests/hitl_pending
    name: 查询待人工审批
    description: 查询需要人工审批的大额申请（金额超过阈值）
    kind: query
    operation: list
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [query, hitl]
    needs_hitl: true
    input_schema:
      type: object
      properties:
        threshold:
          type: number
          default: 1000
          description: 金额阈值

  - id: procurement_requests/summary
    name: 审批摘要统计
    description: 获取审批统计摘要
    kind: analytics
    operation: aggregate
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [analytics]
    input_schema:
      type: object
      properties:
        date_from:
          type: string
          format: date
        date_to:
          type: string
          format: date

  # ========== 审批操作 ==========
  - id: procurement_requests/approve
    name: 审批采购申请
    description: 对采购申请单进行审批（同意或拒绝）
    kind: operation
    operation: approve
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [operation, approval]
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

  - id: procurement_requests/batch_approve
    name: 批量审批采购申请
    description: 对符合条件的采购申请单进行批量审批
    kind: operation
    operation: batch_approve
    entity_name: procurement_requests
    applies_to: procurement_requests
    labels: [operation, batch]
    needs_hitl: true
    input_schema:
      type: object
      required: [action]
      properties:
        date_from:
          type: string
          format: date
          description: 开始日期
        date_to:
          type: string
          format: date
          description: 结束日期
        status:
          type: string
          default: pending
          description: 申请状态
        amount_threshold:
          type: number
          description: 金额阈值（自动审批阈值）
        action:
          type: string
          enum: [approve, reject]
          description: 审批动作

# ========== 业务规则 ==========
rules:
  # 规则1: 大额申请需要人工审批
  - id: rule_auto_approval_threshold
    name: 自动审批阈值规则
    description: 金额不超过1000元的申请可自动审批
    condition: "amount <= 1000 AND status == 'pending'"
    action: "auto_approve"

  # 规则2: 大额申请需要人工审批
  - id: rule_hitl_threshold
    name: 人工审批阈值规则
    description: 金额超过1000元的申请需要人工审批
    condition: "amount > 1000 AND status == 'pending'"
    action: "require_hitl"

  # 规则3: 同一申请人单日申请限额
  - id: rule_daily_limit
    name: 单日申请限额规则
    description: 同一申请人单日申请总额不超过50000元
    condition: "sum(amount) by applicant, date > 50000"
    action: "reject"
"""
