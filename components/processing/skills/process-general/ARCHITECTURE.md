# General Process Subskill Architecture

The subskill inherits the TSAO G0–G18 state machine and supplies a non-polymer process ontology and execution path.

## Decision layers

1. **Need and product/service layer** — specification, throughput, purity, form, regulatory and customer constraints.
2. **Chemistry layer** — stoichiometry, reaction network, catalyst/reagent, impurity and hazard basis.
3. **Measurement layer** — sampling, analytical qualification, data reconciliation and uncertainty.
4. **Property layer** — phase equilibrium, caloric, transport, electrolyte/solids and materials data.
5. **Unit-operation layer** — reactor, separation, recycle, utilities, finishing and waste treatment.
6. **Dynamic layer** — start-up, shutdown, disturbances, constraints, control and protection handoffs.
7. **Scale layer** — lab, continuous bench, pilot, demonstration and industrial representativeness.
8. **Assurance layer** — evidence/claim graph, model risk, scale-up claims, change propagation and independent review.
9. **Delivery layer** — design basis, PFD/stream tables, equipment/utility basis, operating window, qualification, commissioning and technology transfer.

## Domain overlays

`bioprocess`, `electrochemical`, `solids`, `fine-chemical-batch` and `petrochemical` router domains activate specialized checklists but use the same canonical project records. This avoids incompatible project formats while preserving domain-specific science and safety constraints.

## Software neutrality

The canonical evidence, material, stream, reaction, model, Gate and acceptance records remain outside any simulator. DWSIM/CAPE-OPEN, IDAES, Cantera, Pyomo, CoolProp, commercial simulators and multiphysics tools act as adapters and must return versioned, reviewable outputs to the project digital thread.

## Universal executable package contract

`tsao.process_package` validates design basis, streams, equipment, mass/energy closure, utilities, controls, HSE, evidence, acceptance and named approvals for every routed process family.
