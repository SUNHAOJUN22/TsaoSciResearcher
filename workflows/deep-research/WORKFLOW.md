# deep-research

## Purpose
执行可审计检索、筛选、证据提取和冲突综合

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 建立概念块、别名和布尔式
2. 记录数据库、日期、过滤器和检索版本
3. 去重并执行题名/摘要/全文筛选
4. 精确定位方法、参数、结果和限制
5. 保留相反证据并定义停止规则

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
