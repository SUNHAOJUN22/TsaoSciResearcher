# Phase A2 reaction network and state generator

Phase A2 is a software-structure milestone. It turns the Phase A1 catalogs into deterministic state
and reaction objects but intentionally stops before rate evaluation and integration.

## State generation

`skills.epdm.state_generator.generate_state_definition` expands the versioned state catalog by:

- model level 1, 2 or 3;
- active-site family identifiers;
- E, P and D terminal identities;
- declared state basis and energy formulation.

The result contains stable state IDs, contiguous indices, units, non-negativity flags, active-site
inventory groups, vector pack/unpack helpers and a canonical SHA-256 digest.

## Reaction topology

`skills.epdm.reaction_network.build_reaction_network` constructs explicit channels for activation,
initiation, terminal propagation, chain transfer, hydrogen inhibition, deactivation and optional TDB
chemistry. Moment effects are stored as symbolic rules because Phase A2 does not implement moment RHS
equations.

The structural stoichiometric matrix covers explicit generated states. The audit verifies:

- complete site×terminal×incoming propagation topology;
- known state references and deterministic matrix shape;
- separate mechanism families;
- active-site inventory conservation;
- state-definition and canonical-digest identity.

Calling `reaction_network_rhs` raises `A2NumericalExecutionError`. This is deliberate: a structural
PASS does not imply calibrated kinetics, numerical convergence, scientific validation or engineering
approval.
