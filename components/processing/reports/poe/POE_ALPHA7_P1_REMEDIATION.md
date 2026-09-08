# POE alpha.7 P1 remediation

## Closed software gaps

- added bounded first-order fitting, finite-difference Jacobian and identifiability checks;
- added PFR, CSTR and CSTR-series known solutions plus heat-removal margin;
- added property error metrics, power-law viscosity and heat-transfer margin;
- added FOPDT response, transition metrics and recycle-memory reference;
- added dimensionless groups and tolerance-based similarity audit;
- added model-asset passport Schema and controlled registry;
- upgraded the process-package auditor to structured-record hashes, evidence-decision status, model passports and cross-reference validation;
- added `tsao poe` commands, P1 audit, wheel payload and installed-runtime checks.

## Deliberately open external Gates

Historical MATLAB equation confirmation, licensed Aspen/Origin restoration, independent parameter fitting, recycle closure, industrial dynamic assets, CFD/equipment design, HSE, customer qualification and plant guarantees remain `NOT_EVALUATED` or `HOLD`.

## Local source and wheel qualification

- full repository tests: **158/158 PASS**;
- POE core branch coverage: **79%** against a 75% gate;
- P0 closure: **PASS** (139 assets, 18 requirements, seven conflicts, twelve modules, eleven fixture domains);
- P1 reference audit: **PASS_WITH_EXTERNAL_HOLDS**;
- wheel member audit: **PASS**;
- pure-wheel installed-runtime audit: **PASS**.

Ruff and dependency integrity are also mandatory in the clean GitHub matrix. These software results do not change any external scientific or engineering approval state.
