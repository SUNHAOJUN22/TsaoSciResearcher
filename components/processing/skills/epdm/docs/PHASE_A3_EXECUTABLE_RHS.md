# EPDM Phase A3 executable RHS

Phase A3 adds a **software-verified, calculated-reference** rate and RHS layer on top of the frozen Phase A2 state layout and reaction topology.

## Contract

Every reaction channel must bind a stable `rate_law_id`, `parameter_set_id`, required reactant states, required modifiers, SI rate units, Arrhenius temperature dependence, an applicability domain, uncertainty and identifiability states, and evidence references. Missing bindings or parameters return `HOLD`; malformed units or incompatible state references fail closed.

The executable form is:

`dn/dt = N r(n, p, T, V) + Fin - Fout + declared moment-source terms`

`N` is the Phase A2 stoichiometric matrix. Moment-source terms implement the Phase A2 moment rules for live, dead and optional TDB chains and are reported separately from external feed and outflow terms.

## Verification boundary

Allowed status language:

- `STRUCTURAL_PASS`
- `RHS_SOFTWARE_VERIFIED`
- `CALCULATED_REFERENCE_ONLY`

The deterministic reference parameter package uses synthetic fixtures. It is not a scientific calibration and does not establish engineering, HSE, customer or industrial approval. Those statuses remain `NOT_EVALUATED`.
