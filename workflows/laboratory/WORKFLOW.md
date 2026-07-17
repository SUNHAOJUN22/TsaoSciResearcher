# laboratory

## Purpose
管理SOP、批号、样品链、仪器校准、QC、偏差和CAPA

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 冻结SOP版本和安全审批
2. 登记材料批号和样品ID
3. 检查仪器ID与校准状态
4. 安排空白/参考/QC样
5. 保留环境、原始数据、偏差和CAPA

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
