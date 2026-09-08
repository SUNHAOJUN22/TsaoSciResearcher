# DCS/MCSOMe/DMOS Figure Playbook

Use this project-specific mapping together with `figure-standard.md`. The image numbers refer to the user-approved reference-image set.

| Reference image | Figure type and construction | Project use | Placement |
|---|---|---|---|
| 1 | Align compounds by column. Pair each ESP surface with its area-distribution histogram. Place HOMO/LUMO surfaces around one common energy axis. | Integrated DCS/MCSOMe/DMOS electronic-structure comparison. | Main or Extended Data |
| 2 | Show HOMO-2, HOMO-1, HOMO, LUMO, LUMO+1, and LUMO+2 with orbital energy and fixed phase colors. For open-shell systems separate alpha/beta channels and identify SOMO explicitly. | Orbital-composition window for representative Ti complexes. | Extended Data |
| 3 | Put atom charges, dipole vector, and dipole magnitude on the left; use the corresponding ESP surface on the right; compare two states vertically. | Charge-transfer and polarization changes before and after Ti or TEA coordination. | Main or Extended Data |
| 4/8/12 | Use regular ESP cards containing two anchored views, a fixed-bin area histogram, ESP minimum/maximum, and optional MPI. | Complete ESP atlas for 39 independent structures. | SI only |
| 5 | Place matched HOMO/LUMO or SOMO/LUMO surfaces, energies, and fixed phase colors in dense cards. | Frontier-orbital atlas for monomer conformers and representative complexes. | SI |
| 6 | Render one identical cube with two renderers using the same camera, isovalue, density surface, unit, and color scale. | Gaussian/GaussView-style versus VMD renderer consistency check. It is one result, not two scientific observations. | QA only |
| 7 | Arrange substitution types by column; use structure at top, LUMO in the middle, HOMO at the bottom, and one shared ESP comparison. | Primary DCS/MCSOMe/DMOS substitution-effect figure. | Main |
| 9 | Combine parity/residual plots, data distributions, correlation matrix, held-out validation, and explainability. | Do not use for the current 39-structure set. Enable only after an independent, adequately sized dataset and external validation exist. | Conditional |
| 10 | Use a compact 2+1 layout: matched HOMO and LUMO above one larger ESP surface. | High-resolution summary card for an accepted representative structure. | Extended Data or graphical summary |
| 11 | Place orbitals and a common energy axis above, the mechanistic/free-energy relationship in the center, and matched ESP surfaces below. | Core mechanism figure linking orbital evidence to pi/O coordination competition and ESP interpretation. | Main |

## Fixed Project Figure Set

Unless the evidence changes, construct the manuscript around:

1. **Figure 1 - Substitution and conformational space**: structures, conformer coverage, and data lineage.
2. **Figure 2 - Thermochemistry**: conformer free energies, Boltzmann weights, solvent effects, and method spread.
3. **Figure 3 - Substituent electronic effects**: image-7 architecture for structures, frontier orbitals, and ESP.
4. **Figure 4 - Ti coordination competition**: pi/O coordination geometry and free-energy differences with uncertainty.
5. **Figure 5 - Electronic mechanism**: image-11 architecture with SOMO/LUMO, ESP, NBO/QTAIM/NCI, and the scoped mechanistic interpretation.
6. **Figure 6 - Decision and evidence boundary**: candidate conclusion, unresolved differences, model limits, and next falsification calculation.

Move the full orbital manifold to Extended Data and the 39-structure ESP/orbital galleries to SI.

## Data Availability Rules

- Generate only panels supported by accepted source artifacts.
- Use HOMO/LUMO for closed-shell monomers.
- Use alpha-SOMO/alpha-LUMO, beta orbitals where relevant, and spin density for open-shell Ti complexes.
- Do not draw an IRC or potential-energy profile when no validated TS/IRC artifacts exist.
- Do not infer Ti poisoning from isolated-monomer orbitals or ESP alone.
- Do not enable ML/SHAP because multiple calculations derived from one parent structure are not independent samples.

## Rendering and Assembly

- Render molecular surfaces with VMD/Tachyon using the shared camera registry.
- Assemble labels, axes, energy levels, histograms, and multi-panel layouts with a vector plotting backend.
- Use one global ESP scale and one histogram bin definition within each chemical comparison.
- Store every panel's source-data CSV/JSON, renderer script, figure manifest, artifact IDs, and SHA256.
