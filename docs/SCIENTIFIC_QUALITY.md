# Executable scientific quality guards

TsaoSciResearcher 0.5.3 adds three deterministic, host-independent checks. They are deliberately narrow: they prevent missing boundaries and unsupported wording, but they do not decide whether the underlying scientific evidence is true.

## Measurement Boundary

Requires an explicit measurand, method, sample, conditions, unit, calibration/reference and uncertainty. Missing calibration or uncertainty blocks the result; missing applicability or exclusions produces a warning.

## Structure-Property Planner

Requires a three-stage chain:

```text
measured structure -> measurable mediator -> target property
```

This prevents a direct jump from a structural observation to a performance claim. The planner records evidence classes, alternative explanations and a testable prediction.

## Causality Guard

Compares claim wording with the declared design. Causal wording is blocked when the record is observational and does not address confounding or intervention. Mechanism and uncertainty omissions are reported independently.

## CLI

```bash
python -m tsao_researcher quality examples/scientific-quality-check.json
```

The output is JSON with `PASS`, `WARN` or `BLOCK`, stable finding codes and machine-readable details.

## Visual verification

- [`research-quality-dashboard.html`](research-quality-dashboard.html)
- [`research-quality-dashboard.svg`](research-quality-dashboard.svg)
- [`engineering-audit-report.pdf`](engineering-audit-report.pdf)

These artifacts are generated and checked in CI. They are demonstrations of software guard behavior, not approval of a scientific conclusion.
