# Thermochemistry, bond energies, redox and kinetics

## Reaction and activation free energies

\[
\Delta G_{\mathrm{rxn}}=G_{\mathrm{products}}-G_{\mathrm{reactants}}
\]

\[
\Delta G^{\ddagger}=G_{\mathrm{TS}}-G_{\mathrm{reference}}
\]

Use one temperature, solvent and standard state. For solution reactions, account
for the 1 atm ↔ 1 mol L⁻¹ convention according to the change in molecularity.

## Low-frequency entropy

Weak complexes and flexible molecules can receive unrealistic harmonic entropy.
Use a documented qRRHO/quasi-harmonic treatment and preserve both raw and
corrected values.

## Rate estimates

Classical transition-state theory:

\[
k=\kappa\frac{k_BT}{h}\exp\left(-\frac{\Delta G^{\ddagger}}{RT}\right)
\]

State reaction order, standard state, transmission/tunneling correction,
path degeneracy and whether diffusion or solvent friction is neglected.

## BDE/BDFE

For homolysis `A–B → A• + B•`:

\[
\mathrm{BDE}=H(A^{\bullet})+H(B^{\bullet})-H(A-B)
\]

\[
\mathrm{BDFE}=G(A^{\bullet})+G(B^{\bullet})-G(A-B)
\]

Optimize and validate each radical; check multiplicity and spin contamination.
Distinguish electronic `D_e`, zero-point-corrected `D_0`, enthalpy and free energy.

## Binding and interaction energy

\[
E_{\mathrm{int}}=E_{AB}-E_A-E_B
\]

Use a declared geometry convention and inspect BSSE/counterpoise for small
basis sets. Binding free energy additionally depends on entropy, solvation,
standard state and conformer ensembles.

## Redox potential

Do not substitute HOMO energy for an oxidation potential. Compute and validate
oxidized/reduced states, solvation and reference-electrode conversion. Relative
calibration to a reference couple can cancel systematic error when performed at
one consistent protocol.
