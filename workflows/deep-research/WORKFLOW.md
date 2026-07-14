# Deep research and evidence mapping

设计检索、筛选与证据映射，保留来源和冲突。

Indexed capabilities routed here: **16**.

## Inputs

- `research_question`
- `scope`
- `date_range`
- `source_constraints`

## Required outputs

- `search_strategy`
- `evidence_map`
- `source_log`
- `research_gap_report`

## Evidence rules

Search broadly enough to represent competing findings. Prefer primary sources for claims about methods and results. Record search date, database, query, filters and stable locator. Never invent a DOI or infer a paper's content from title alone.


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
- `references/literature/search-and-evidence.md`
- `references/integrity/claim-evidence-policy.md`

Templates:
- `templates/evidence-map/evidence-record.json`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
