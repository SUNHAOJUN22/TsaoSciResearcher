# Technical report and decision communication

把研究证据转化为技术报告、阶段总结和领导决策材料。

Indexed capabilities routed here: **3**.

## Inputs

- `project_context`
- `methods`
- `results`
- `audience`

## Required outputs

- `technical_report`
- `executive_summary`
- `figures`
- `action_items`


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
- `references/writing/technical-reporting.md`
- `references/visualization/plotting-standards.md`

Templates:
- `templates/technical-report/technical-report.md`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
