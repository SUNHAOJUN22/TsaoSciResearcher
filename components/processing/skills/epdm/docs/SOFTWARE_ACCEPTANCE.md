# EPDM software-acceptance closure

## Acceptance command

```bash
python -m tsao.cli epdm qualify-acceptance \
  --project skills/epdm/fixtures/v2_phase_a1_reference_project.json \
  --output reports/runtime/EPDM_SOFTWARE_ACCEPTANCE.json \
  --load-samples 7
```

The command is the governed software-acceptance entry point. It performs the following sequence without re-indexing the source JSON after canonical publication:

1. strict JSON parsing, schema validation and explicit `2.0.0 → 2.0.0` migration;
2. frozen dataclass construction and temporary `ContractRegistry` reference closure;
3. immutable canonical publication and repeated-load identity check;
4. A2 generated-state and reaction-network construction from the canonical snapshot;
5. full 41-binding A3 synthetic reference package audit;
6. A4 adaptive Dormand–Prince 5(4) execution of a source-bound analytic activation case;
7. analytic-solution, conservation, monotonic-time, loader latency and peak-memory Gates;
8. machine-readable report emission.

## Acceptance thresholds

| Gate | Threshold |
|---|---:|
| Canonical-loader median time | ≤ 0.5 s |
| Canonical-loader peak traced memory | ≤ 64 MiB |
| Analytic activation absolute error | ≤ 1×10⁻⁷ |
| A2 network audit | PASS |
| Full A3 rate-package audit | PASS |
| A4 adaptive integration | PASS |
| Canonical publication identity | stable across repeated loads |

The resource limits are regression ceilings for the small governed fixture, not industrial throughput claims.

## Scope boundary

The numerical execution uses `SYNTHETIC_REFERENCE_NOT_PROJECT_CALIBRATION`. A software PASS proves reproducible contract loading, structural network closure, executable reference numerics and packaging/runtime integrity. It does not approve kinetic parameters, thermodynamics, reactor design, HSE, customer qualification or industrial performance. Those remain `NOT_EVALUATED` until named external evidence and accountable approval exist.
