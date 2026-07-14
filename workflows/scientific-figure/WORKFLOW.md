# Scientific figure contract and production

先定义图的科学结论与证据职责，再绘图、导出和视觉质检。

Indexed capabilities routed here: **2**.

## Inputs

- `data`
- `figure_conclusion`
- `audience`
- `export_requirements`

## Required outputs

- `figure_contract`
- `plot_code`
- `figure_files`
- `qa_report`

## Figure contract gate

Before code, create a valid figure contract containing the core conclusion, audience, panel responsibilities, data provenance, axes, units, uncertainty, statistics, legend, export formats and review risks. Validate it with `python scripts/validate_figure.py <contract.json>`.

Default plotting profile is Python/Matplotlib, 450 DPI raster preview, SVG or PDF vector export when appropriate, no decorative grid, explicit units and retained code/data. Zero-origin axes are used only when scientifically meaningful.


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
- `references/visualization/figure-contract.md`
- `references/visualization/plotting-standards.md`

Templates:
- `templates/figure-contract/figure-contract.json`

## Completion criteria

- Inputs, assumptions and exclusions are recorded.
- Material claims are linked to evidence or explicitly labeled as inference/hypothesis/recommendation.
- Required human approvals are recorded.
- Outputs pass the relevant schema and semantic validators.
- Limitations and unresolved conflicts remain visible.
