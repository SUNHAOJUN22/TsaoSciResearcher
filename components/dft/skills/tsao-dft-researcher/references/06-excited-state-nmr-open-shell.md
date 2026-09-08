# Excited states, NMR and open-shell systems

## TD-DFT

Report vertical excitation energy/wavelength, oscillator strength and state
character. For mixed transitions, prefer NTO hole/particle pairs over a long
list of orbital promotions.

During excited-state optimization, track state identity using excitation energy,
oscillator strength, NTOs/transition density and hole-electron descriptors.
A fixed `Root` number can change physical character after state reordering.

For S0/S1/T1 comparisons, use validated structures and report bond-length,
angle and dihedral changes with a clear atom-index convention.

## Hole-electron and NTO analysis

Record the TD state, analysis definition, grid and descriptors such as overlap,
centroid separation and transfer distance. An isosurface shows location, not the
magnitude of transferred charge by itself.

## Open-shell and triplet calculations

- document charge and multiplicity;
- report `<S²>` before/after annihilation against the ideal value;
- perform stability analysis when needed;
- inspect α/β orbitals and spin density;
- consider multiple spin states or broken-symmetry solutions where chemically
  justified.

## NMR

Use GIAO shielding at a declared level and solvent. Convert shielding to chemical
shift with a same-method reference or validated regression:

\[
\delta_i=\sigma_{\mathrm{ref}}-\sigma_i
\]

For flexible molecules, compute conformer-weighted shielding and preserve the
weighting protocol. Shielding values are not chemical shifts until referenced.
