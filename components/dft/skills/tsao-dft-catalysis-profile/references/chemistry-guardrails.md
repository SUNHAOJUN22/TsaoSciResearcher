# Catalysis Chemistry Guardrails

## Model matrix

Record monomer identity, substituent pattern, conformer, Ti coordination mode, TEA/ion-pair state, charge, multiplicity, solvent model, and stoichiometry as separate controlled variables.

## Balanced comparisons

Use balanced thermodynamic cycles for coordination, ligand exchange, and deactivation. A lower total energy for a larger complex is not evidence of stronger coordination.

## Open-shell Ti

For every candidate state:

- evaluate plausible multiplicities;
- check wavefunction stability and S^2;
- inspect spin density and chemically sensible orbital occupancy;
- report alpha/beta frontier orbitals rather than forcing closed-shell HOMO/LUMO language;
- avoid comparing different spin states with inconsistent methods or solvation.

## Poisoning language

Use the following hierarchy:

1. **coordination propensity** supported by balanced free energies;
2. **electronic/structural rationale** supported by complementary descriptors;
3. **kinetic inhibition hypothesis** only with barriers or a justified microkinetic bridge;
4. **catalyst poisoning** only when the modeled deactivation state and experimental context support persistence or irreversible loss of activity.

## Evidence combinations

- Geometry + free energy: coordination preference.
- Free energy + TS/IRC: pathway plausibility.
- ESP/orbitals/NBO/QTAIM/IRI/IGMH: mechanistic interpretation.
- Experiment/literature: bridge to catalyst performance.
