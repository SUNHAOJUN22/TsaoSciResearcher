# Laboratory workflow and traceability

建立SOP、样品编码、仪器数据、QC、ELN和实验室自动化流程。

Indexed capabilities routed here: **8**.

## Inputs

- `protocol_goal`
- `materials`
- `instruments`
- `safety_constraints`

## Required outputs

- `sop`
- `sample_plan`
- `qc_plan`
- `traceability_records`


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
- `references/experimental-design/laboratory-quality.md`
- `references/integrity/integrity-gates.md`

Templates:
- `templates/experiment-protocol/protocol.yaml`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
