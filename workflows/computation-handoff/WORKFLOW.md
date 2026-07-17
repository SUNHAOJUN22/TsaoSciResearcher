# computation-handoff

## Purpose
生成绑定项目、输入、方法、收敛、验证和审批的计算合同

## Use when
Use for the workflow intent routed by Router v2.

## Do not use when
Do not use it to fabricate evidence, execution, validation or acceptance.

## Entry criteria
- scientific objective recorded
- inputs classified by provenance

## Execution phases
1. 读取项目、问题、假设和证据ID
2. 选择领域profile和候选方法
3. 登记输入文件、单位、版本、许可和校验和
4. 定义边界、资源、收敛、不确定性和物理验证
5. 设置审批、结果回执和接受/拒绝门

## Decision tree
- unavailable tools produce a plan or handoff, not fake results
- contradictory results trigger review, not suppression
- high-risk final decisions require qualified approval

## Failure and recovery
Record the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.

## Completion
Required artifacts exist, claims are traceable and limitations remain visible.
