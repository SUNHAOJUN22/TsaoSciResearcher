# Scientific writing and publication

根据证据链写作论文，控制结论强度并维护引用完整性。

Indexed capabilities routed here: **14**.

## Inputs

- `research_question`
- `evidence`
- `results`
- `target_format`

## Required outputs

- `structured_draft`
- `claim_evidence_map`
- `citation_check`
- `revision_log`

## Claim discipline

Write from an approved claim-evidence map. Use calibrated verbs: observed, associated, predicted, supports, suggests and demonstrates are not interchangeable. Preserve conditions, sample scope, uncertainty and alternative explanations.


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
- `references/writing/scientific-writing.md`
- `references/integrity/claim-evidence-policy.md`

Templates:
- `templates/manuscript/manuscript-outline.md`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
