# VMD and Tachyon reproducible rendering

## Rendering contract

Every render records:

- cube/structure source and volume index;
- VMD version and renderer;
- representation, atom radii and bond style;
- camera matrix/view, orthographic or perspective projection;
- positive/negative isovalues;
- volume color scale and numerical limits;
- material, opacity, background and image dimensions;
- post-processing, if any.

## Orbital surfaces

Use equal-magnitude positive and negative isosurfaces. Colors represent phase;
the caption must say so. Keep one view and one isovalue across an orbital gallery.
For HOMO/LUMO comparison, annotate exact orbital indices and energies from the
same calculation level.

## ESP surfaces

Map ESP onto a fixed electron-density surface. For molecule-to-molecule
comparison, lock density isovalue, ESP range, color map, camera and scale. If an
individual auto-range is used for exploratory viewing, state that colors are not
cross-comparable.

## Interaction surfaces

IRI/IGMH/NCI colors must be tied to the displayed scalar and numerical range.
Do not use a generic blue/green/red legend without defining attraction,
near-zero/dispersion and repulsion for that exact plot.

## Output

- Use TachyonInternal/Tachyon or another documented renderer, not a desktop
  screenshot.
- Keep molecular renders as high-resolution raster (typically PNG/TIFF) while
  axes, energy levels, histograms and labels remain vector when assembled.
- Inspect final-size framing: no clipped atoms, hidden active sites, illegible
  labels or excessive empty space.
