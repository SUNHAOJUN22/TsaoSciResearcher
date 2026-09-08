# Patent and technology transfer support

支持检索、专利地图、现有技术初筛、交底和TRL评价；不替代法律意见。

Indexed capabilities routed here: **7**.

## Inputs

- `technical_solution`
- `search_scope`
- `claims_or_features`

## Required outputs

- `search_strategy`
- `landscape`
- `risk_flags`
- `disclosure_draft`


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
- `references/project-governance/patent-and-transfer.md`
- `references/integrity/claim-evidence-policy.md`

Templates:
- `templates/patent-and-transfer/invention-disclosure.md`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
