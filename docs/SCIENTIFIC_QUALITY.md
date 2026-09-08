# Executable scientific-quality guards

TsaoSciResearcher 0.7.0 provides four deterministic, host-independent controls. They constrain operational completeness and claim strength; they do not decide whether the underlying science is true.

## Measurement Boundary

Requires the measurand, method, sample, conditions, unit, calibration/reference, uncertainty, applicability, exclusions, replication, data reduction, detection limit and traceability.

## Structure–Property Planner

Records processing/intervention, structure, measurable mediator, target response, evidence, confounders, alternative explanations, validation strategy, uncertainty, scale bridge, statistical basis and conservation constraints.

## Causality Guard

Compares English or Chinese causal wording with the declared design. Observational evidence cannot silently become an intervention-supported causal conclusion. Confounding, temporal order, replication, mechanism testing and uncertainty are represented separately.

## Evidence Traceability

Links claim IDs to evidence IDs, source locators, roles and uncertainty. A claim that an external task completed is blocked unless execution receipts are present.

## CLI and visual evidence

```bash
python -m tsao_researcher quality examples/scientific-quality-check.json
```

- [`research-quality-dashboard.html`](research-quality-dashboard.html)
- [`research-quality-dashboard.svg`](research-quality-dashboard.svg)
- [`engineering-audit-report.pdf`](engineering-audit-report.pdf)

PASS/WARN/BLOCK results demonstrate software guard behavior, not scientific approval.
