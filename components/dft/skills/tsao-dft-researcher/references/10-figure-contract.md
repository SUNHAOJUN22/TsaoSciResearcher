# Computational-chemistry figure contract

A figure starts with a claim and required evidence, not with a screenshot.

## Universal checklist

- one-sentence scientific claim;
- panel-to-evidence map;
- source files and validation states;
- common comparison settings;
- quantity/unit/sign/reference definitions;
- readable final-size typography;
- editable SVG/PDF for numerical elements;
- high-resolution raster for molecular surfaces;
- caption containing method, state, isovalue and color meaning;
- visual inspection plus `validate_figure_spec.py` and `qa_bundle.py`.

## Archetypes from the reference images

### 1. Multi-orbital energy panel

Required: orbital cubes, exact indices/energies, common isovalue and camera,
energy-level scale and HOMO-LUMO gap. Verify orbital ordering; LUMO+n energies
must increase consistently. Phase colors are not charge.

### 2. Atomic charge/dipole plus ESP

Name the charge scheme, units and color range. Define the dipole-arrow convention.
ESP must state density surface, potential units and sign colors.

### 3. ESP histogram plus energy alignment

Use identical histogram bins/range and declare whether the ordinate is area,
area fraction or grid count. Energy levels share one zero/reference and scale.

### 4. ESP extrema gallery

Automate cards from one specification. Report `Vmin`, `Vmax`, extrema locations,
area distribution and whether color limits are global or local.

### 5. HOMO/LUMO gallery

Fix card size, molecule orientation, orbital isovalue, phase colors, decimal
precision and energy method. Add gap values when scientifically relevant.

### 6. Dopant/functional-group matrix

Keep parent skeleton size, substitution position, charge/state and rendering
parameters comparable. Separate structural model, orbital evidence and ESP
interpretation.

### 7. DFT + machine-learning composite

Prediction plots require untouched test data, `y=x`, metrics, folds/seeds and
uncertainty. Correlation heatmaps define coefficient. SHAP/importance panels
state the exact importance definition and do not imply causality.

### 8. Single-molecule HOMO/LUMO/ESP triad

Use the same molecular view for orbitals, equal isovalues and a symmetric ESP
scale when appropriate. Add energies/gap and a caption that distinguishes phase
from electrostatic potential.

### 9. Multi-molecule energy alignment + PET schematic + ESP

Energy levels must use one physical reference. A PET arrow is a mechanistic
hypothesis unless supported by excited-state/redox/free-energy evidence. ESP
panels use common scales.

## Figure-type routing

- Numerical axes or exact data → Python/Matplotlib, vector export.
- Molecular scalar field → Multiwfn/cube + VMD/Tachyon.
- Final composite → assemble validated raster and vector assets without altering
  quantitative data.
- AI-generated mechanism/graphical abstract → label as schematic draft; never use
  it for numerical evidence or invented molecular surfaces.
