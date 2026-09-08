# Experimental design and measurement plan

建立因子、响应、对照、重复、功效、DOE和质量控制方案。

Indexed capabilities routed here: **3**.

## Inputs

- `hypotheses`
- `factors`
- `responses`
- `constraints`

## Required outputs

- `experimental_design`
- `sample_size`
- `randomization_plan`
- `analysis_plan`

## Design checks

Identify experimental unit, observational unit, factors, levels, responses, nuisance variables and batch structure. Justify controls, randomization, blinding, replication and sample size. Predefine exclusions and stopping rules.


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
- `references/experimental-design/doe-and-power.md`
- `references/experimental-design/laboratory-quality.md`

Templates:
- `templates/experiment-protocol/protocol.yaml`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
