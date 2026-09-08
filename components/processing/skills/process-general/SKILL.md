---
name: TSAO-PROCESS-GENERAL
version: 0.3.0
inherits: ../../SKILL.md
---

# General Chemical Process Development Subskill

Use this pack for catalytic and non-catalytic reactions, petrochemical/refining, fine-chemical batch, biochemical, electrochemical, crystallization/solids, formulation, utilities, retrofit, debottlenecking, troubleshooting and package audit.

It is a decision system, not a setpoint database. Every value from literature, patents, suppliers, simulations or inherited cases remains screening evidence until the active project qualifies identity, units, measurement boundary, applicability and uncertainty.

## Mandatory causal chain

`requirement → reaction network → feed/impurity specification → measurement → thermodynamics/transport → reactor → separation/recycle → utilities → dynamics/control → HSE/reliability → pilot/scale-up → TEA/LCA → package/acceptance → field learning`

## Fourteen modules

1. chemistry and reaction basis;
2. measurement and data qualification;
3. thermodynamics and properties;
4. reactor and transport engineering;
5. separation and recycle;
6. control and operability;
7. HSE and reliability;
8. scale-up and pilot design;
9. TEA, LCA and supply chain;
10. bioprocess overlay;
11. electrochemical overlay;
12. solids and crystallization overlay;
13. fine-chemical batch overlay;
14. petrochemical and refining overlay.

Each module must define a decision question, scope/Gate interface, qualified inputs, equations or algorithms, executable workflow, counterfactual or falsification, uncertainty/applicability domain, failure modes, quantitative exit criteria, outputs, interfaces, external accountable work and tests.

## Route and model rules

- preserve at least one technically distinct route until evidence closes the choice;
- distinguish intrinsic kinetics from mixing and heat/mass-transfer limitations;
- qualify VLE/LLE/SLE, enthalpy, density, viscosity and transport properties against independent evidence;
- close mass, element, charge, energy, impurity, water, VOC and carbon balances;
- model recycle impurity accumulation and purge explicitly;
- evaluate start-up, shutdown, utility loss, off-spec handling and emergency response;
- state preserved physics, broken similarity and compensating evidence for every scale-up claim;
- require independent review for high-consequence models and package release.

## Domain overlays

- **Bioprocess:** state, sterility, OUR/OTR, kLa, rheology, inhibition, contamination and downstream recovery.
- **Electrochemical:** charge balance, Faradaic efficiency, polarization, ohmic/transport loss, gas evolution, heat and degradation.
- **Solids/crystallization:** supersaturation, nucleation/growth/agglomeration, polymorph, PBM/PSD, filtration, drying, dust and electrostatics.
- **Fine chemical:** dosing trajectory, accumulation, selectivity, calorimetry, cleaning, campaigns and recipe genealogy.
- **Petrochemical/refining:** feed envelope, catalyst deactivation, fractionation, hydrogen/steam/flare networks, integrity and energy integration.

## Fail-closed conditions

HOLD when chemistry or balance is unresolved, a property method is only a simulator default, parameters confound transport, calorimetry is missing for exothermic service, recycle impurities are unclosed, a separation is idealized outside its domain, failure response is absent, scale-up uses ratios alone, or technical approval is inferred from a simulation or laboratory result.

## Required outputs

Produce the master TSAO artifacts plus reaction-basis, property-method, reactor-selection, separation/recycle, utilities, operability, HSE/reliability, pilot/scale-up, TEA/LCA and process-package acceptance dossiers.

## Universal executable package contract

`tsao.process_package` validates design basis, streams, equipment, mass/energy closure, utilities, controls, HSE, evidence, acceptance and named approvals for every routed process family.
