# patent-and-transfer

## Purpose
支持特征拆解、检索、专利地图、FTO风险和技术交底

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 拆解技术特征和候选权利要求
2. 组合关键词与IPC/CPC
3. 聚合同族、优先权和法律状态
4. 评价相关性与覆盖
5. 生成风险信号、律师复核点和TRL

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
