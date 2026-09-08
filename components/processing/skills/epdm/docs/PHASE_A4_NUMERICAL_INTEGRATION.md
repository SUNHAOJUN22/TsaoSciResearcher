# EPDM Phase A4 / Alpha.15 numerical integration

Phase A4 adds an opt-in adaptive Dormand–Prince 5(4) integration layer above the locked Phase A3 structural RHS.

## Software contract

Every request records the parameter-bundle, rate-package, generated-state and reaction-network identifiers; time interval; step bounds; tolerances; maximum attempts; non-negative-state policy; conservation policy; applicability requirement; software qualification boundary; and scientific approval state.

The integrator:

- rejects invalid identifiers, booleans used as numerics, NaN/Infinity, reverse time and invalid step/tolerance ranges;
- propagates Phase A3 HOLD/FAIL decisions without inventing default parameters;
- rejects and reduces steps that create negative intermediate or candidate states, clamping only round-off values within the declared tolerance;
- reports suspected stiffness, minimum-step exhaustion and maximum-step-count exhaustion as machine-readable HOLD states;
- records accepted/rejected attempts, monotonic times, embedded error estimates and explicit external-flow integrals;
- verifies named site inventories, total polymer-unit inventory and the Phase A3 E/P/D static conservation ledgers.

## Boundary

The implementation uses synthetic calculated-reference parameters and is software verification only. It does not establish calibrated kinetics, GPC/PBM validity, reactor design, HSE approval, customer qualification or industrial performance.
