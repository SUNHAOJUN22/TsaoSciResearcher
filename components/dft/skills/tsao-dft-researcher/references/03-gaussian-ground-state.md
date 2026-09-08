# Gaussian ground-state, conformer and minimum workflow

## Standard chain

```text
identity/protonation/state review
→ conformer search and duplicate removal
→ low-cost preoptimization
→ DFT Opt
→ Freq at the same level
→ minimum and wavefunction checks
→ optional higher-level SP
→ thermochemistry and property handoff
```

## Minimum acceptance

- Gaussian completed without unresolved SCF/optimization warnings.
- Zero chemically meaningful imaginary frequencies. Tiny soft modes require
  visual inspection and may need tighter optimization/integration settings.
- Geometry still represents the intended molecule, coordination and conformer.
- Charge/multiplicity are documented.
- Open-shell cases pass S² and stability review.
- Low-energy conformers are not omitted without a declared scope.

## Conformer ensembles

Validate each conformer before Boltzmann weighting. Remove duplicates using
geometry/energy criteria and consider symmetry or degeneracy. Ensemble free
energy can be expressed as:

\[
G_{\mathrm{ens}}=-RT\ln\sum_i \exp(-G_i/RT)
\]

Do not present raw harmonic populations as precise when low-frequency modes,
solvation or incomplete sampling dominate the uncertainty.

## Output discipline

Every reported energy must state its type and unit: electronic energy, E+ZPE,
enthalpy or Gibbs free energy. Preserve original `.log` and `.chk`; generate
`.fchk` with the matching Gaussian utility only after the run is identified.
