# TsaoSciComputation handoff

把真实计算需求转换为有输入、边界、验证和审批的标准任务。

Indexed capabilities routed here: **4**.

## Inputs

- `scientific_question`
- `target_property`
- `available_inputs`
- `constraints`

## Required outputs

- `validated_handoff`
- `method_candidates`
- `validation_requirements`
- `approval_points`

## No simulated execution

Do not create fake output or state that software was run. Specify scientific question, target property, scale, candidate methods, inputs, boundary conditions, convergence checks, uncertainty analysis, expected outputs, evidence level and human approval points.


## Universal execution order

1. Confirm the decision or scientific question.
2. Classify provided material as user-provided, sourced, observed, calculated, inferred or hypothetical.
3. Define inputs, exclusions, assumptions and acceptance criteria before analysis.
4. Execute only tools actually available in the active environment.
5. Record artifacts and evidence IDs.
6. Run the workflow-specific checks.
7. Assign a state: completed, checked, validated, accepted/rejected.
8. Report limitations and unresolved decisions.

## Load on demand

References:
- `references/computation/handoff-protocol.md`
- `references/project-governance/scientific-validation.md`

Templates:
- `templates/computation-handoff/computation-handoff.json`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
