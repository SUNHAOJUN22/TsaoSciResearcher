# TSAO Architecture

TSAO is a contract-driven skill system, not a monolithic prompt.

## Layers

1. **Interaction layer** — project brief, user decisions and explicit approval points.
2. **Research layer** — planner/executor/publisher orchestration, evidence ledger, standards and IP mapping.
3. **Science layer** — chemistry, thermodynamics, kinetics, transport, population balances and data reconciliation.
4. **Process layer** — route synthesis, reactors, separation/recycle, utilities, dynamic control and operability.
5. **Scale layer** — lab, continuous bench, pilot, demonstration and industrial representativeness.
6. **Assurance layer** — typed assurance graph, model risk, Gate state machine, change propagation and independent review.
7. **Delivery layer** — process package, commissioning, qualification, transfer and field feedback.
8. **Software supply-chain layer** — schemas, tests, manifests, SBOM, deterministic archive and cleanroom validation.

## Typed digital thread

`requirement → claim → source → hypothesis → experiment → sample → method → dataset → model → parameter → design → equipment/control/barrier → test → gate → change → release → field evidence`

A high-consequence claim must have a continuous support path. Orphaned nodes, expired evidence, unresolved contradictions or unreviewed MR4/MR5 models block the relevant Gate.

## Specialist model

Every project activates at least one specialist contract while retaining the master G0–G18 rules:

- `process-general` — non-polymer reaction, property, reactor, separation, control, HSE and scale-up method;
- `epdm` — EPM/EPDM catalyst-to-customer lifecycle;
- `poe` — SJTU-derived POE solution-polymerization and package-acceptance method;
- `polymer-general` — other polymerization, modification and formulation routes.

A specialist skill supplies domain ontology, decision logic, models, templates and tests. It may narrow the master rules but may not weaken traceability, fail-closed Gates or approval boundaries. Generic domain labels such as bioprocess, electrochemical, solids, fine-chemical-batch and petrochemical route through `process-general` until a deeper domain pack is activated.

## Simulator neutrality

The canonical project model is stored in TSAO schemas. DWSIM, IDAES, Cantera, Pyomo, CoolProp, Aspen and other tools are adapters. This prevents a project from becoming inseparable from one vendor file and makes cross-tool verification possible.

## Source-core and complete-distribution boundary

The GitHub source core contains the installable master kernel and reviewable specialist contracts. The independently qualified complete distribution also contains the full EPDM v9, SJTU-POE and universal-polymer source trees. Public ingestion of those assets must retain per-file provenance, license isolation and inherited tests; an opaque archive is not a substitute for reviewable source.

## Qualification boundary

Repository CI qualifies code and data contracts only. Scientific validity, engineering design, process safety, FTO, customer approval and industrial performance remain `NOT_EVALUATED` until real evidence and named accountable reviewers are present.

## Alpha.8 package platform

`tsao.process_package` is the universal executable content contract. EPDM is the flagship specialist adapter; POE remains the evidence-rich specialist adapter.

## Alpha.15 executable integration layer

EPDM Phase A4 is an opt-in numerical layer above the locked A2 state/network topology and A3 calculated-reference RHS. It uses a self-contained Dormand–Prince 5(4) implementation with explicit tolerances, bounded step control, non-negative-state rejection, monotonic time, restart parity and named conservation ledgers. Solver execution remains `CALCULATED_REFERENCE_ONLY`; parameter calibration and all scientific, engineering, HSE, customer and industrial approvals remain `NOT_EVALUATED`.
