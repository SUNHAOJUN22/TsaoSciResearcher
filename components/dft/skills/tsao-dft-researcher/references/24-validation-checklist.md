# Validation Checklist

## Planning

- One falsifiable question and allowed conclusion set.
- Balanced reference states and model scope.
- Existing artifacts inventoried before new work.
- Method, basis, solvent, charge, multiplicity, temperature, and standard state declared.
- Estimated task count, wall time, CPU, RAM, disk, and user approval recorded before long external execution.

## Gaussian and Electronic Structure

- Input syntax and atom count checked.
- SCF convergence and wavefunction stability reviewed.
- Minimum has zero imaginary frequencies.
- TS has one intended imaginary mode.
- Forward and reverse IRC connect the intended endpoints.
- Open-shell `<S²>` and spin density reviewed.
- TDDFT state identity and NTO character tracked.
- NMR reference and shielding-to-shift conversion declared.

## Thermochemistry

- Electronic energy, ZPE, enthalpy, and Gibbs energy labeled separately.
- Temperature and standard state consistent.
- qRRHO parameters reported when used.
- Boltzmann weights normalized stably.
- BDE/BDFE definitions and fragment multiplicities correct.
- BSSE correction not mislabeled as a free-energy correction.
- Redox thermodynamic cycle and reference electrode explicit.

## Wavefunction Analysis

- Source wavefunction accepted and hashed.
- Grid, geometry, method, basis, charge, and multiplicity match comparisons.
- ESP scale and histogram bins fixed within a group.
- MO phase colors and isovalues fixed.
- Open-shell orbital labels correct.
- QTAIM, NBO, NCI/IRI/IGMH interpretations remain descriptor-specific.

## Figures

- Quantitative panels have CSV/JSON source data.
- Each panel has artifact IDs and complete method metadata.
- Camera, crop, atom style, scale, isovalue, and color convention are consistent.
- Vector and high-resolution raster exports exist as appropriate.
- No rainbow palette, clipped labels, overlaps, blank panels, or illegible text.
- Final PDF rendered page-by-page and inspected.

## Claims and Reports

- Every numerical claim maps to source data and accepted artifacts.
- Evidence, inference, and hypothesis are separated.
- Method sensitivity and unresolved differences are visible.
- No mock or incomplete result is promoted.
- No static DFT result is silently extrapolated to kinetics or material performance.
- Independent methods, mechanism, visualization, and reproducibility reviews completed.
