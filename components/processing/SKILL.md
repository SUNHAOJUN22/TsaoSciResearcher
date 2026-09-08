---
name: TSAO-PROCESSING-SKILL
description: Universal chemical-process research, development, scale-up, qualification and technology-transfer operating system with process-general, EPDM, POE and polymer-general specialist routes.
version: 0.1.0-alpha.15
license: Apache-2.0
---

# TSAO Process Intelligence OS

## 1. Activate and route

Use TSAO to develop, evaluate, model, scale up, troubleshoot, retrofit, optimize, qualify, transfer or audit a chemical process or technology package.

Keep this master contract active and add the relevant specialist:

- general reaction, separation, biochemical, electrochemical, solids, petrochemical or batch process → `skills/process-general/SKILL.md`;
- EPM/EPDM → `skills/epdm/SKILL.md`;
- POE solution polymerization → `skills/poe/SKILL.md`;
- other polymerization, modification, formulation or reactive processing → `skills/polymer-general/SKILL.md`.

The output is an auditable development programme and reusable artifacts—not a literature summary, an attractive flowsheet or an unsupported process package.

## 2. Non-negotiable rules

1. Define decisions, boundaries, owners and acceptance criteria before drawing a flowsheet.
2. Keep `OBSERVED`, `REPORTED`, `CALCULATED`, `INFERRED`, `ASSUMED`, `PROPOSED`, `PLANNED`, `REJECTED` and `APPROVED` states distinct.
3. Record claim-level source locators, dates, applicability, contradictions and review expiry.
4. No literature, patent, supplier or inherited-case value becomes a design or production setpoint without project validation.
5. Every model declares purpose, risk class, equations, units, parameters, data lineage, identifiability, uncertainty, applicability domain and independent validation.
6. Every scale-up claim states preserved physics, broken similarity, compensating evidence, residual risk and rollback criteria.
7. Every Gate is fail-closed. Missing evidence means `HOLD` or `NOT_EVALUATED`, never implicit PASS.
8. Software-artifact qualification is separate from scientific, engineering, safety, legal, customer and industrial approval.
9. HAZOP/LOPA/SIL, relief design, FTO, customer qualification, pilot operation and plant trials remain accountable external work unless actually executed.
10. Produce machine-readable records and reusable project files, not only narrative advice.

## 3. Mandatory actions for one complete invocation

A complete invocation must perform, or explicitly schedule with blockers:

1. classify project mode, chemistry, phase regime, operation mode, product form, limiting physics and hazards;
2. recursively inventory supplied files and build source, data, conflict, assumption and gap registers;
3. define falsifiable questions, competing hypotheses, counterfactual routes, discriminating experiments and acceptance criteria;
4. instantiate G0–G18 work packages with owner, input, output, dependency, fallback and residual risk;
5. create the charter, target profile, CQA/CMA/CPP matrix, experiment plan, model architecture, scale-up register, package index and acceptance matrix;
6. run evidence, chemistry, analytical, statistics, properties, kinetics, reactor, separation, control, HSE, reliability, economic, environmental and IP-interface workstreams;
7. block data leakage, unidentifiable parameters, conservation errors, citation mismatch, hidden assumptions and unsupported extrapolation;
8. preserve truthful states: an unrun experiment, unavailable commercial model or unsigned safety study remains `PLANNED` or `REQUIRES_EXTERNAL_EXECUTION`;
9. publish decisions, evidence, calculations, models, process-development results, scale-up claims, package records and unresolved blockers;
10. run project, source, release and approval-boundary audits before delivery.

## 4. G0–G18 lifecycle

- **G0** mandate, scope, ownership and governance
- **G1** evidence, standards, patents and knowledge gaps
- **G2** product/application requirements and CQA
- **G3** analytical methods, raw materials, data and measurement systems
- **G4** chemistry route and catalyst concept
- **G5** mechanism, kinetics, thermodynamics and property basis
- **G6** laboratory feasibility and safe operating envelope
- **G7** model qualification and identifiability
- **G8** continuous bench and dynamic validation
- **G9** separation, recovery, finishing and recycle closure
- **G10** pilot design basis
- **G11** pilot execution, reconciliation and model update
- **G12** demonstration and scale representativeness
- **G13** industrial flowsheet, equipment, utilities and emissions
- **G14** control, digital twin, transitions and operability
- **G15** HSE, reliability, TEA, LCA, supply chain and IP
- **G16** product, customer and regulatory qualification
- **G17** package freeze, commissioning and performance test
- **G18** post-commercial monitoring, MOC and continuous learning

Allowed status: `NOT_EVALUATED`, `HOLD`, `CONDITIONAL`, `PASS`, `FAIL`, `RETIRED`.

## 5. Parallel professional workstreams

Every project instantiates 14 workstreams; reduced depth requires a recorded rationale:

1. governance and decision rights;
2. evidence, standards, patents and knowledge graph;
3. product/application quality and customer needs;
4. raw materials, catalysts, impurities and chemistry;
5. sampling, analytical methods and data systems;
6. DoE, statistics, inference and uncertainty;
7. mechanism, kinetics and population distributions;
8. thermodynamics, rheology, phase behaviour and transport;
9. reactors, multiphysics and numerical models;
10. separation, recovery, recycle, finishing and process synthesis;
11. laboratory, bench, pilot, demonstration and industrial scale-up;
12. steady state, dynamics, control, operations and reliability;
13. safety, environment, economics, supply chain and IP interfaces;
14. reports, process package, acceptance and transfer.

## 6. Execution sequence

1. Parse the brief into decisions, constraints, unknowns, hazards and stakeholders.
2. Route the task and initialize the project workspace.
3. Build the evidence ledger and typed assurance graph before major claims.
4. Establish material, sample, method, instrument and dataset passports.
5. Preserve at least two technically distinct routes until evidence closes the choice.
6. Design experiments for discrimination, parameter identifiability and information value.
7. Build the minimum defensible model hierarchy and reject unidentifiable complexity.
8. Close mass, element, charge, energy, impurity, utility, water, VOC and carbon balances as applicable.
9. Advance through scales only by explicit Gate evidence.
10. Trace every package requirement to a source, dataset, model, test and approval.
11. Run `tsao doctor`, project audit and release validation.
12. Deliver the package with open blockers and external handoffs visible.

## 7. Maturity

- **M0 idea** — goal only
- **M1 evidence-framed** — scope, evidence and questions defined
- **M2 chemistry-proven** — chemistry and measurement repeatable
- **M3 laboratory-process-proven** — laboratory window and model basis qualified
- **M4 bench-integrated** — coupled process and recycle demonstrated
- **M5 pilot-ready** — pilot design, safeguards and learning plan ready
- **M6 pilot-proven** — pilot data validate scale claims
- **M7 demo-proven** — representative continuous operation and product qualification
- **M8 industrial-ready** — design, controls, safety, economics and package acceptable
- **M9 operationally-validated** — industrial performance, reliability and transfer closed

Document completeness alone never raises maturity.

## 8. Default deliverables

Create the charter/RACI, requirement and causal matrices, evidence and contradiction registers, standards/patent/FTO handoffs, material/sample/method/dataset passports, experiment plan and batch records, qualified model dossiers, balances, PFD basis and stream/equipment/control records, scale-up and uncertainty registers, HSE/reliability/TEA/LCA handoffs, pilot and performance-test protocols, package index, acceptance matrix, transfer plan and field-monitoring plan.

## 9. Verification and trust boundary

- `doctor --profile core` verifies the public source identity.
- `doctor --profile full` also verifies the complete distribution manifest, checksums, SBOM and release identity.
- Deterministic source snapshots and full distributions are separate artifacts with separate hashes.
- Tool availability, versions, methods, tolerances and independent checks must be recorded.
- EPDM v9, SJTU-POE and universal-polymer inherited data remain reference-only until the active project validates identity, units, measurement boundary, property method, equipment geometry, operating envelope and uncertainty.

Physical experiments, commercial simulation, engineering design, safety studies, FTO, customer qualification, pilot/demonstration and industrial performance remain `NOT_EVALUATED` until supported by real evidence and named qualified approval.
