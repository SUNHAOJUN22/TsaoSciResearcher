# Model qualification

## Risk classes

- MR1: descriptive or exploratory, no direct design consequence.
- MR2: screening or experiment planning.
- MR3: scale-up or operating-window support with bounded consequence.
- MR4: equipment, control, safety or customer decision support.
- MR5: high-consequence or performance-guarantee decision support.

## Qualification dossier

Every qualified model records purpose, risk class, equations, variables and units, assumptions, parameters, calibration data, validation data, preprocessing, identifiability, uncertainty, sensitivity, applicability domain, software/solver configuration, residual diagnostics, alternatives, limitations, reviewer and version hash.

## Minimum tests

- mass, element, energy and relevant population conservation;
- dimensional consistency;
- known analytical or independent numerical solution;
- limiting behaviour and monotonicity where physically required;
- structural/practical identifiability;
- sensitivity and uncertainty propagation;
- independent batches, scales or operating regimes;
- extrapolation and out-of-domain refusal;
- change and drift detection.

MR4/MR5 qualification requires named independent review. Calibration fit alone is never qualification.
