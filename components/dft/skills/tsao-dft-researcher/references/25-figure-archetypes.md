# Computational-Chemistry Figure Archetypes

Choose the smallest figure architecture that directly answers the scientific question. A figure is an evidence interface, not a gallery of everything the software can export.

## 1. Orbital Manifold

Use when nearby occupied or virtual orbitals affect the interpretation.

- Arrange HOMO-2 through LUMO+2 around one shared energy axis.
- Use the same molecular orientation, crop, phase colors, and isovalue for every orbital.
- State whether values are canonical Kohn-Sham orbital energies, not optical gaps.
- For open-shell systems, separate alpha/beta channels and label SOMO explicitly.

## 2. Matched HOMO/LUMO or SOMO/LUMO Gallery

Use for comparing many molecules or states.

- One card per accepted structure.
- Fixed orbital isovalue, camera registry, atom palette, lighting, and image dimensions.
- Include orbital index, energy, charge, multiplicity, and method fingerprint.
- Do not resize individual molecules independently to exaggerate delocalization.

## 3. ESP Surface plus Distribution

Use when the claim concerns electrostatic regions, polarity, or intermolecular recognition.

- Map ESP to one declared electron-density isosurface.
- Use one symmetric scale and one histogram bin definition within a comparison group.
- Report extrema, area-weighted statistics, positive/negative surface area, and MPI when relevant.
- State the color-sign convention; do not infer reaction barriers from color alone.

## 4. Charge, Dipole, and ESP Composite

Use when a perturbation changes polarization or charge redistribution.

- Place atomic charges or charge differences and the dipole vector beside the matched ESP panel.
- Use the same charge partitioning method across systems.
- Keep dipole direction conventions explicit.
- Pair qualitative surfaces with quantitative values and uncertainty or method spread.

## 5. Interaction Atlas

Use for IRI, IGMH, NCI/RDG, QTAIM, NBO, or difference-density evidence.

- State fragment definitions, isovalue, sign(lambda2)rho range, and grid.
- Use surfaces to locate interactions, not to rank strength by color area alone.
- Pair with interaction energy, integrated descriptor, bond critical point data, NBO donor-acceptor terms, or another quantitative observable.

## 6. Free-Energy and Mechanism Figure

Use only after references, stationary points, and relevant IRC paths are validated.

- Plot relative Delta G or Delta E, never bare total energies.
- State reference state, temperature, solvent, standard state, and correction scheme.
- Distinguish computed pathway, hypothesis, and illustrative arrows.
- Mark unresolved branches or method-sensitive orderings rather than forcing one pathway.

## 7. Excited-State Evidence Figure

Use for absorption, emission, charge transfer, or state character.

- Combine spectrum or excitation table with NTO/hole-electron panels.
- Record state index, excitation energy, oscillator strength, broadening, and solvent.
- Track state identity across geometry optimization; root number alone is not an identity proof.

## 8. DFT plus Machine-Learning Dashboard

Use only when molecules are independent enough for a defensible validation split.

- Include split strategy, sample count, parity, residuals, uncertainty, applicability domain, and external or scaffold-held-out validation.
- Use SHAP or feature importance only after leakage checks.
- Multiple conformers, charge states, or calculation levels from one parent molecule are not automatically independent samples.

## 9. Compact 2+1 Summary Card

Use for one representative accepted structure.

- Matched HOMO and LUMO (or SOMO/LUMO) above one larger ESP panel.
- Include essential energies and the shared surface parameters.
- Suitable for graphical summaries, not as a substitute for complete SI evidence.

## 10. Renderer QA

Use to test reproducibility of the visualization pipeline.

- Render the same cube with identical camera, isovalue, scale, and sign convention.
- Treat renderer comparisons as QA, never as independent scientific observations.

## Placement

- **Main text:** the minimum set needed to support the central claims.
- **Extended Data:** alternate views, sensitivity, method checks, and representative manifolds.
- **Supporting Information:** complete structure, frequency, orbital, ESP, interaction, and provenance galleries.
- **QA only:** renderer comparisons, camera tests, nonblank-image checks, and output-bundle audits.
