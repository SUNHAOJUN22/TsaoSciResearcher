# data-analysis

## Purpose
从数据生成机制出发执行质量、统计、UQ与科学ML

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 登记来源、许可、校验和与单位
2. 检查缺失、重复、异常、批次和物理边界
3. 识别依赖、聚类、删失和重复测量
4. 选择统计或ML子协议并诊断假设
5. 报告效应量、区间、多重性、泄漏和适用域

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
