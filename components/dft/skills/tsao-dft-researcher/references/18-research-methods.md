# Research Methods

## Contents

1. Research framing
2. Ground-state workflow
3. Reaction mechanisms
4. Excited states and spectra
5. Thermochemistry
6. Interaction and electrochemistry
7. Method sensitivity

## 1. Research Framing

Translate the scientific question into:

- species and balanced reference states;
- observables that can support or falsify the hypothesis;
- required calculations and validation tests;
- allowed conclusions and forbidden extrapolations;
- experimental observables that can test the prediction.

Do not choose a functional or basis only because it is familiar. Match the method to bonding, dispersion, charge transfer, transition metal, open-shell, excited-state, and solvent requirements. Reproduce a cited method when replication is the goal; disclose every deviation.

## 2. Ground-State Workflow

1. Generate chemically distinct conformers.
2. Pre-screen only to select starting geometries.
3. Optimize each retained conformer.
4. Run frequency analysis at the optimization level.
5. Apply a larger-basis single point when justified.
6. Construct RRHO or declared qRRHO thermochemistry.
7. Compute Boltzmann populations with log-sum-exp.

For each structure preserve coordinates, charge, multiplicity, method, basis, solvent, grid, SCF settings, temperature, standard state, output hash, and frequency verdict.

## 3. Reaction Mechanisms

Build a balanced path:

```text
reactants -> encounter complex -> TS -> intermediate/product
```

Use scans only to generate candidates. Validate a transition state by:

- one imaginary frequency;
- normal-mode displacement along the intended bond changes;
- forward and reverse IRC endpoints;
- endpoint optimization when IRC endpoints are not fully relaxed;
- consistent electronic state and stoichiometry.

Report:

\[
\Delta G^\ddagger = G_{\mathrm{TS}} - G_{\mathrm{reference}}
\]

\[
\Delta G_{\mathrm{rxn}} = G_{\mathrm{product}} - G_{\mathrm{reference}}
\]

\[
k = \kappa\frac{k_BT}{h}\exp\left(-\frac{\Delta G^\ddagger}{RT}\right)
\]

State the transmission coefficient assumption and standard state. A TS without validated IRC is a candidate, not a confirmed mechanism.

## 4. Excited States and Spectra

- Use TDDFT vertical excitations for absorption assignments.
- Optimize the relevant excited state before discussing excited-state geometry or emission.
- Track state identity across optimization; do not rely only on root number.
- Prefer NTOs over long lists of canonical orbital transitions.
- Report oscillator strengths, dominant configurations or NTO weights, state character, solvent model, and broadening used for spectra.
- For triplets and radicals, check multiplicity, stability, spin contamination, and spin density.

For NMR, calculate shielding tensors with GIAO and convert to shifts with a declared reference compound or calibrated regression. Never compare shieldings and experimental shifts as if they were identical.

## 5. Thermochemistry

Keep these quantities distinct:

- `D_e`: electronic dissociation energy;
- `D_0`: dissociation energy including ZPE;
- BDE: bond dissociation enthalpy at the stated temperature;
- BDFE: bond dissociation free energy;
- reaction enthalpy and Gibbs free energy.

Use:

\[
\mathrm{BDE}_{A-B}(T)=H_A(T)+H_B(T)-H_{A-B}(T)
\]

For association:

\[
\Delta G_{\mathrm{bind}}=G_{\mathrm{complex}}-\sum_iG_{\mathrm{fragment},i}
\]

State the 1 atm/1 M convention. Counterpoise corrects electronic BSSE; it does not by itself produce a corrected Gibbs free energy.

## 6. Interaction and Electrochemistry

- Compute interaction energies with balanced fragments and a defined geometry convention.
- Distinguish relaxed binding energy from frozen-fragment interaction energy and deformation energy.
- Use explicit solvent molecules when proton transfer or specific solvation dominates.
- Build redox potentials from a thermodynamic cycle, solvation free energies, and an explicit reference electrode:

\[
E^\circ=-\frac{\Delta G^\circ_{\mathrm{redox}}}{nF}+E^\circ_{\mathrm{reference}}
\]

HOMO energy alone is not a redox potential.

## 7. Method Sensitivity

Use a second defensible functional or basis when:

- competing states differ by less than the declared uncertainty;
- transition-metal spin states are close;
- charge-transfer excitation is central;
- dispersion controls conformer ordering;
- a mechanistic conclusion changes near a threshold.

If the method spread overlaps the observed difference, report the candidates as unresolved rather than ranking them artificially.
