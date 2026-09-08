# EPDM Phase A0 hardening plan

## Objective

Close the software-safety and evidence-governance gaps before any EPDM V2 scientific-contract or
equation work begins. V1 public names and numerical outputs remain compatible; unsafe assumptions
must become machine-visible Gates rather than prose-only caveats.

## Work packages

1. **Repository closure** — remove one-time workflows and diagnostic reports; retain one permanent
   read-only CI workflow; regenerate source identity.
2. **Evidence qualification Gate** — recursively resolve all EPDM evidence references against the
   package ledger; fail retracted/superseded evidence; hold provisional evidence; verify locator and
   applicability.
3. **Scientific declaration provenance** — require evidence for catalyst benchmark, active sites,
   diene topology, kinetic parameters, phase stability, mixing and non-equilibrium devolatilization.
4. **Semibatch assumption Gate** — preserve V1 golden numerics while returning
   a governed-case `HOLD` whenever `SEMIBATCH` uses `FIXED_CONCENTRATION_REFERENCE`, while the V1
   calculation result remains numerically and semantically locked.
5. **Schema and API contracts** — strict EPDM case schema, typed evidence ledger, V1 public signature
   lock, return-envelope lock and golden-output lock.
6. **Negative testing** — cover malformed nested sections, duplicate/missing evidence, invalid evidence
   states, applicability mismatch and unexpected-exception detection.
7. **Qualification evidence** — bind the hardened source commit to permanent cross-platform CI and
   publish a machine-readable qualification report. Scientific and engineering approvals remain
   `NOT_EVALUATED`.

## Phase boundary

This plan does not implement V2 reaction networks, population balances, parameter estimation, GPC
convolution, uncertainty propagation, CFD, EOS, dynamic control or industrial design qualification.
Those activities remain blocked until Phase A0 is closed.
