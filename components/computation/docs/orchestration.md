# Scientific computation super-skill orchestration

TsaoSciComputation is a fail-closed intermediary between a scientific objective and the functions, libraries, command-line tools, solvers, services, containers, schedulers or Skills that may implement it.

## Nine-stage plan

1. Validate the calculation contract.
2. Select workflow, methods, capabilities and invocation candidates.
3. Probe software, licenses, data, hardware and paths.
4. Prepare native inputs, callable payloads, commands or handoffs.
5. Execute only an authorized, ready target.
6. Parse outputs and evaluate numerical convergence.
7. Check units, conservation, physical plausibility, references and applicability.
8. Quantify statistical, numerical, parameter, model-form and handoff uncertainty.
9. Bind evidence and accept, reject, fall back, escalate or supersede.

## Invocation policy

The repository exposes registered trusted local scientific functions. They may execute through `tsao-computation invoke ... --execute` and return request/result hashes plus timing evidence. External adapters, Python modules, CLI programs, remote APIs, containers, scheduler jobs, commercial tools and other Skills are plan-only by default. Registration never authorizes arbitrary imports, shell commands, network access or licensed solver execution.

## Acceleration policy

Acceleration advice spans profiling, native backends, analytic Jacobians, sparse preconditioning, multigrid/domain decomposition, adaptive stepping, continuation/warm starts, parallel independent cases, streaming memory, batching/vectorization, mixed precision, surrogate/reduced-order models and checkpoint/restart. Every recommendation records applicability, expected benefit type, precision or determinism risks, requirements, validation and whether it is actually measured.

## Trust boundary

`completed != parsed != converged != physically validated != uncertainty quantified != accepted`. Detecting hardware or building a command is planning evidence, not proof of speedup or scientific validity.
