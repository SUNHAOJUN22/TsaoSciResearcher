# project-management

## Purpose
通过事件状态、检查点、风险和产物血缘治理科研项目

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 建立WBS、所有者和依赖DAG
2. 定义里程碑和验收标准
3. 记录风险、决策和审批
4. 创建检查点并检测陈旧产物
5. 从哈希事件链恢复状态

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
