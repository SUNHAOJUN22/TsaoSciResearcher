# Research program management

管理工作包、状态、依赖、里程碑、风险、决策和交付物。

Indexed capabilities routed here: **17**.

## Inputs

- `objectives`
- `work_packages`
- `resources`
- `constraints`

## Required outputs

- `project_plan`
- `milestones`
- `risk_register`
- `status_dashboard`


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
- `references/project-governance/state-model.md`
- `references/project-governance/scientific-validation.md`

Templates:
- `templates/project-plan/project-plan.yaml`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
