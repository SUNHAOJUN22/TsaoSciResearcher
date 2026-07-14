# Peer review and response audit

从科学问题、方法、统计、图表、引用和复现性审查稿件。

Indexed capabilities routed here: **3**.

## Inputs

- `manuscript`
- `supplement`
- `review_scope`

## Required outputs

- `review_report`
- `major_concerns`
- `minor_comments`
- `decision_rationale`


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
- `references/writing/peer-review.md`
- `references/integrity/integrity-gates.md`

Templates:
- `templates/review-response/response-to-reviewers.md`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
