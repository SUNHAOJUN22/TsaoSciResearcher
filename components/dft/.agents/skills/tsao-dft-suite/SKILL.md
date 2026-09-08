---
name: tsao-dft-suite
description: Use for TsaoDFT_skill parser contracts, Gaussian/VASP/QE/CP2K outputs, transition-state theory, standard states, DFT-to-ML provenance, quantity shape, model cards, or claims of accepted external DFT execution. Activate on requests to accept a run without complete output or independent evidence so it is held. Do not use for generic quantum-chemistry teaching, unrelated coding, or prose-only editing.
license: Apache-2.0
compatibility: Windows and Linux Skill suite. Real Gaussian, VASP, QE, or CP2K qualification requires external execution evidence and independent scientific approval.
metadata:
  author: "SUNHAOJUN22"
  version: "16.0.0"
  repository: "TsaoDFT_skill"
---
# TSAO DFT suite

## Workflow

1. Route every legacy engine parser through one fail-closed state contract.
2. Give fatal, abort, truncation, and non-convergence markers precedence over earlier success.
3. Preserve quantity kind, unit, shape, component convention, atom mapping, aggregation, and source locator.
4. Require an explicit activity/standard-state convention for multi-molecular TST.
5. Bind dataset validation, trainer inputs, model, code, environment, applicability domain, calibrated uncertainty, holdout evidence, and independent approval.
6. Reject Bool, NaN, infinity, unknown units, and self-issued accepted status.
7. Run focused parser/TST/model counterexamples, then the repository-native permanent gates.

## Transition-state contract

\[
k_n=\kappa\frac{k_BT}{h}\exp\left(-\frac{\Delta G^{\ddagger,\circ}}{RT}\right)(c^\circ)^{1-n}.
\]

## Truth boundary

Without exact external engine outputs and independent review preserve `EXTERNAL_DFT_EXECUTION_NOT_VERIFIED`.
