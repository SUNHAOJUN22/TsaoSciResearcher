# Publication Figure Standard

## Figure Architecture

Use a small set of reusable scientific archetypes:

1. **Substitution comparison**: columns are compounds; rows are structure, frontier orbitals, ESP, and key descriptors.
2. **Orbital manifold**: HOMO-2 through LUMO+2 around one shared energy axis.
3. **Charge/dipole/ESP comparison**: atomic charge and dipole panel beside one matched ESP panel.
4. **ESP gallery**: two anchored views, area histogram, extrema, MPI, and one group-wide scale.
5. **Orbital gallery**: matched HOMO/LUMO or SOMO/LUMO cards for many structures.
6. **Energy-mechanism-surface composite**: quantitative energy levels or free-energy profile, mechanistic diagram, and selected electronic surfaces.
7. **Renderer QA**: compare two renderers using the same cube, surface, scale, and camera; never present this as independent scientific evidence.
8. **ML diagnostics**: parity, residuals, external validation, correlation, and explainability only when sample independence and validation are adequate.
9. **Compact 2+1 summary card**: matched HOMO and LUMO surfaces above one larger ESP surface for a single accepted representative structure.

## Main, Extended Data, and SI

- Main text: 4-6 figures, each answering one scientific question.
- Extended Data: sensitivity, alternate views, method checks, and descriptor matrices.
- SI: complete structure, orbital, ESP, frequency, and provenance galleries.
- QA-only material: renderer comparisons, non-empty pixel tests, and camera checks.

## Molecular Rendering

- Use the same chemical anchor and camera for comparisons.
- Use one atom palette, radius scale, bond style, lighting, background, and crop.
- Prefer VMD/Tachyon ray tracing for final molecular surfaces.
- Preserve transparent or white backgrounds according to assembly needs.
- Do not stretch structures independently to fill panels.

## Surface Parameters

- MO: `±0.020 a.u.` default; representative sensitivity at `±0.015/±0.030`.
- Density surface for ESP: `ρ=0.001 a.u.` unless justified otherwise.
- Spin density and difference density: declare positive and negative isovalues.
- Use fixed phase colors across every MO panel.
- Use one symmetric ESP scale for a comparison group.
- Do not use rainbow colormaps. Prefer perceptually uniform, colorblind-safe sequential or diverging maps.

## Quantitative Plots

- Derive plots from CSV/JSON source data.
- Use SI units or discipline-standard units consistently.
- Show uncertainty as intervals or method spread; do not imply precision beyond the calculation.
- Use vector PDF/SVG for axes, text, and line art.
- Use 89 mm single-column or 183 mm double-column layouts unless the target journal specifies otherwise.
- Target 7-9 pt final text and at least 0.5 pt final line width.
- Use direct labels where practical and minimize decorative legends.

## Required Panel Metadata

Each panel must expose, in the caption or manifest:

- source artifact IDs;
- method, basis, solvent, temperature, charge, and multiplicity;
- analysis type and software/version;
- units, isovalue, density surface, and color scale;
- renderer, camera ID, grid, and downsampling;
- evidence grade and known limitation.

## Scientific Labeling

- Use eV for orbital energies, D for dipole moments, `e` for atomic charges, Å for distance, Å² for area, and kcal mol⁻¹ or kJ mol⁻¹ for thermochemistry.
- Label open-shell Ti or radicals with alpha/beta SOMO/LUMO and spin density, not closed-shell HOMO/LUMO by habit.
- Never mix a.u. and kcal mol⁻¹ on one ESP scale without conversion.
- Keep color sign conventions explicit in every caption.

## Export and QA

- Surface images: lossless PNG/TIFF; 600 dpi for line-containing composites.
- Quantitative figures: PDF/SVG plus source data.
- Verify non-empty pixels, no clipping, no overlap, embedded fonts, colorblind readability, grayscale readability, and panel-caption correspondence.
- Render final PDF pages to images and inspect every page.
