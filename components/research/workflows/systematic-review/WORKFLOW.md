# Systematic review and evidence synthesis

执行协议化检索、筛选、质量评价和证据综合。

Indexed capabilities routed here: **5**.

## Inputs

- `protocol`
- `eligibility_criteria`
- `databases`
- `screening_records`

## Required outputs

- `prisma_log`
- `included_studies`
- `quality_assessment`
- `evidence_synthesis`

## Protocol gate

Freeze the question, eligibility criteria, databases, search strings, deduplication rule, screening process, extraction fields and quality tool before synthesis. Preserve excluded records with reasons. Do not call a narrative search a systematic review.


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
- `references/literature/systematic-review.md`
- `references/statistics/method-selection.md`

Templates:
- `templates/literature-matrix/literature-matrix.csv`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
