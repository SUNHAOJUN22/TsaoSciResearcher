# scientific-figure

## Purpose
先建立图形合同再绘图与最终尺寸质检

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 映射claim—evidence—panel
2. 定义数据源、转换、坐标、单位和统计
3. 定义样本量、不确定性和可访问配色
4. 保留绘图代码与数据血缘
5. 执行矢量/栅格导出、校验和和最终尺寸检查

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
