# TSAO alpha.11 performance optimization plan

Date: 2026-07-27  
Authoritative branch: `main`  
Starting release: `0.1.0-alpha.10`

## Objective

Improve throughput and memory behavior for large scientific sweeps and long dynamic studies without weakening public validation, numerical precision, output contracts or approval boundaries.

## Work packages

### P0 — expanded evidence baseline

- Freeze the alpha.10 runtime for 64/512 EPDM site families.
- Measure scalar 1,000-scenario EPDM screening.
- Measure 10,000-step EPDM semibatch and POE RK4 runs.
- Measure 10,000-point dynamics, 500/5,000-equipment packages and 300/3,000-file provenance.
- Include Doctor, Skillpack inventory and Wheel member verification.
- Record median/min/max/stdev, warm-ups, traced peak memory, result digest and top cumulative profile rows.

### P1 — EPDM batch-screening kernel

Implement a NumPy broadcasting interface for temperature, residence time, active-site concentration and propagation multipliers.

Acceptance criteria:

- scalar and batch scenario records match within declared floating-point tolerances;
- all shape, finite-value, positivity and broadcasting errors fail closed;
- the scalar API remains unchanged;
- the 1,000-scenario workload demonstrates a meaningful speedup;
- returned arrays include explicit shape and axis semantics;
- status remains `CALCULATED_REFERENCE_ONLY`.

### P1 — EPDM semibatch trajectory

Refactor the single conservative step into a validated internal kernel and expose a trajectory function.

Acceptance criteria:

- public one-step results remain unchanged;
- trajectory validation is performed once at the boundary;
- every recorded step preserves non-negative inventories and positive temperature;
- cumulative material closure remains within the existing tolerance;
- default behavior records every step; any future reduced-history mode must be explicit and must not replace the full-history default.

### P1 — POE fixed-state RK4 kernel

Replace the remaining dataclass/getattr-heavy inner loop with a fixed-order tuple representation while preserving the public dataclass API and complete history.

Acceptance criteria:

- terminal state, time grid, history values, molecular metrics and error paths match the scalar reference;
- no public field is removed;
- 400-step and 10,000-step workloads improve or remain within the declared non-regression floor;
- a separate terminal-only API may be added for online loops, but it must be explicitly named and must not change `simulate_kinetics`.

### P2 — large-package and provenance scale checks

- Verify near-linear scaling from 500 to 5,000 equipment items.
- Verify near-linear scaling from 300 to 3,000 source files.
- Reject optimizations that hide evidence checks or reduce error localization.

### P2 — persistent performance contract

- Upgrade the benchmark schema.
- Add peak-memory and scale-efficiency metrics.
- Generate bilingual README tables from the versioned comparison report.
- Run the short regression suite in permanent Ubuntu/Python 3.14 CI.
- Keep the expanded suite as release evidence and manual/workflow-dispatch qualification to avoid multiplying hosted-runner cost across all platforms.

## Performance gates

| Workload | Gate |
|---|---|
| Existing alpha.10 protected workloads | at least 0.90× of the alpha.10 median, except universal package floor 0.85× |
| EPDM 512/64 site-family ratio | no superlinear anomaly beyond a documented tolerance |
| EPDM 1,000-scenario batch vs scalar baseline | at least 3×, with matching scenario values |
| EPDM 10,000-step semibatch | at least 1.5× or a documented memory reduction with no timing regression |
| POE 10,000-step RK4 | at least 1.5× with full history retained |
| Dynamics 10,000 points | at least 0.90× |
| 5,000/500 equipment normalized scaling | no hidden superlinear growth beyond measured tolerance |
| 3,000/300 source-file normalized scaling | no hidden superlinear growth beyond measured tolerance |

Microsecond-scale tests use repeated medians on the same runner. Heavy cases use fewer repetitions but retain warm-up, digest and peak-memory checks.

## Release convergence

If code or contracts change, publish `0.1.0-alpha.11` and update every release anchor. Alpha.10 performance reports remain historical and are never overwritten.

The final source tree must contain only the permanent read-only CI workflow. Temporary baseline, diagnostic and promotion workflows must be deleted before the final authoritative commit.
