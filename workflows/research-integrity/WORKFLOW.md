# Research integrity and audit

只读检查引用、数据、统计、图像、结论和AI生成风险。

Indexed capabilities routed here: **8**.

## Inputs

- `manuscript_or_dataset`
- `audit_scope`
- `provenance`

## Required outputs

- `integrity_findings`
- `evidence_log`
- `severity`
- `recommended_actions`

## Read-only default

Do not alter the manuscript, dataset, figure or audit trail unless the user explicitly switches from audit to revision. Report finding, evidence, severity, uncertainty and remediation separately. Do not accuse misconduct from an automated anomaly alone.


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
- `references/integrity/integrity-gates.md`
- `references/integrity/claim-evidence-policy.md`

Templates:
- `templates/research-integrity/audit-plan.yaml`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
