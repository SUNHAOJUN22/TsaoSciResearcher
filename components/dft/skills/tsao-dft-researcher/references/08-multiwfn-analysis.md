# Multiwfn quantitative analysis workflow

Multiwfn is a post-processor, not an upstream validation tool.

## Required record

- input wavefunction file and checksum;
- originating log, method/basis, charge/multiplicity, solvent and state;
- Multiwfn version/build;
- exact menu sequence or reviewed batch input;
- grid spacing/quality and surface definition;
- orbital/state/fragment indices;
- units, cutoff/isovalue and sign/color convention;
- text/table/cube outputs.

## Common routes

1. **MO/SOMO/NTO:** select exact orbital or TD state; export positive/negative
   phase cubes using one shared isovalue for comparisons.
2. **ESP:** calculate surface extrema, positive/negative areas, histogram and
   density/ESP cubes. Use one common density surface and color range for a series.
3. **Charges/bond orders:** use a declared scheme and export tables; never mix
   schemes in one trend without explanation.
4. **Fukui/local reactivity:** verify N±1 state definitions and atom mapping.
5. **IRI/IGMH/NCI/QTAIM:** define fragments, interaction scope and quantitative
   outputs before creating an isosurface.
6. **TD spectra/NTO/hole-electron:** tie all outputs to a validated state number
   and record broadening only for plotted spectra.
7. **ICSS:** preserve magnetic-shielding component and spatial reference.

## Automation rule

Batch/menu scripts are version-sensitive. Generate them as reviewable artifacts,
dry-run where possible, and require explicit execution approval. If a menu route
changes, stop rather than sending speculative keystrokes to production data.
