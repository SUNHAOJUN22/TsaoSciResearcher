# Data quality, statistics and scientific ML

从数据生成机制出发执行质量、统计、不确定性和模型检查。

Indexed capabilities routed here: **52**.

## Inputs

- `dataset`
- `data_dictionary`
- `analysis_question`
- `assumptions`

## Required outputs

- `quality_report`
- `analysis_results`
- `uncertainty`
- `reproducible_code`

## Method-selection gate

Match the method to data type, dependence, distribution, censoring, repeated measures and sampling design. Report effect sizes and uncertainty, not only p-values. Separate exploratory from confirmatory analysis and correct multiplicity when required.


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
- `references/statistics/method-selection.md`
- `references/statistics/uncertainty-and-robustness.md`

Templates:
- `templates/data-manifest/data-manifest.yaml`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
