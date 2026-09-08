# EPDM Phase A2 implementation plan

## Objective

Implement a deterministic V2 reaction-network specification and state generator on top of the
qualified Phase A1 contracts. Phase A2 must make reaction topology, state indexing, structural
stoichiometry, active-site conservation and model-level boundaries executable and testable without
claiming calibrated kinetics or numerical reactor simulation.

## Deliverables

1. A generated, versioned state layout expanded by model level, active-site family and terminal
   identity, with stable indices, vector pack/unpack helpers, non-negativity contracts and canonical
   SHA-256 identity.
2. A structural reaction network containing separate activation, initiation, terminal×incoming
   propagation, transfer, hydrogen inhibition, spontaneous/poison deactivation and optional TDB
   generation/reincorporation channels.
3. A deterministic structural stoichiometric matrix, symbolic moment-update rules and active-site
   inventory conservation audit.
4. Strict Draft 2020-12 schemas for generated state definitions and reaction networks, integrated
   into the V2 project schema and semantic cross-reference validator.
5. A synthetic A2 reference project, machine-readable reaction/state catalogs, updated requirement
   traceability and positive/negative/property-style tests.
6. Cross-platform software qualification bound to the final clean source tree.

## Non-goals

Phase A2 does not evaluate rate laws, bind calibrated parameter values, construct a numerical RHS,
solve ODE/DAE systems, calculate thermodynamic properties, estimate parameters, compute molecular
weight distributions, simulate reactors, localize events or make engineering recommendations.

## Exit criteria

- State generation is deterministic and independent of hard-coded numerical indices.
- The propagation channel set is the exact site×terminal×incoming-monomer Cartesian product.
- Activation and initiation, hydrogen transfer and reversible inhibition, and spontaneous and poison
  deactivation remain separate channels.
- TDB generation and reincorporation are either both absent or both present at model level 3.
- Every reaction references known generated states and preserves each active-site inventory.
- A1 projects remain valid; the A2 reference project passes strict schema and semantic validation.
- V1 APIs and golden numerics remain unchanged.
- Numerical execution remains explicitly `NOT_IMPLEMENTED_PHASE_A2`.
