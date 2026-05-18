"""
采购审批意图定义
"""

PROCUREMENT_INTENTS = """
intents:
  # ========== 采购申请单查询 ==========
  - type: query_procurement_requests
    name: 查询采购申请单
    description: 查询采购申请单列表，支持按日期、状态、金额等条件筛选
    keywords:
      - 采购申请
      - 申请单
      - 待审批
      - 审批
      - 申请
      - procurement
      - purchase request
      - PR
    patterns:
      - ".*采购.*申请.*"
      - ".*申请.*单.*"
      - ".*待审批.*"
      - ".*PR.*"
      - ".*procurement.*"
    actions:
      - procurement_requests/list
      - procurement_requests/query_pending
    examples:
      - "查询今日待审批的采购申请单"
      - "查看本周的采购申请"
      - "有哪些采购申请需要我审批"
      - "列出所有待审批的PR"

  # ========== 审批执行 ==========
  - type: execute_approval
    name: 执行审批
    description: 对采购申请单进行审批操作（同意/拒绝）
    keywords:
      - 审批
      - 审核
      - 批准
      - 同意
      - 拒绝
      - 通过
      - approve
      - review
      - check
    patterns:
      - ".*审批.*通过.*"
      - ".*批准.*"
      - ".*同意.*"
      - ".*拒绝.*"
      - ".*approve.*"
    actions:
      - procurement_requests/approve
      - procurement_requests/reject
    examples:
      - "审批通过PR-2026-0518-001"
      - "批准张三的采购申请"
      - "拒绝金额超过5000的申请"
      - "同意这批采购"

  # ========== 金额条件查询 ==========
  - type: query_by_amount
    name: 按金额条件查询
    description: 按金额大小筛选采购申请
    keywords:
      - 大于
      - 超过
      - 少于
      - 低于
      - 金额
      - amount
    patterns:
      - ".*金额.*大于.*"
      - ".*金额.*超过.*"
      - ".*金额.*少于.*"
      - ".*金额.*低于.*"
    actions:
      - procurement_requests/list
    examples:
      - "查询金额大于1000的申请"
      - "列出超过5000的采购"
      - "找出金额少于500的申请"

  # ========== 批量审批 ==========
  - type: batch_approval
    name: 批量审批
    description: 对多张采购申请单进行批量审批操作
    keywords:
      - 批量
      - 全部
      - 批量审批
      - 全部通过
    patterns:
      - ".*批量.*审批.*"
      - ".*全部.*通过.*"
      - ".*批量.*通过.*"
    actions:
      - procurement_requests/batch_approve
    examples:
      - "批量审批所有小额申请"
      - "把金额小于1000的申请全部通过"
      - "批量同意这批采购"

  # ========== 审批摘要 ==========
  - type: approval_summary
    name: 审批摘要
    description: 查看待审批申请的摘要统计
    keywords:
      - 摘要
      - 统计
      - 汇总
      - summary
      - statistics
    patterns:
      - ".*审批.*摘要.*"
      - ".*审批.*统计.*"
      - ".*审批.*汇总.*"
    actions:
      - procurement_requests/summary
    examples:
      - "审批摘要"
      - "今天需要审批多少单"
      - "本周审批统计"
"""
