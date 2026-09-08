# Wavefunction Analysis

## Input Hierarchy

Prefer accepted `.fchk`, `.wfn`, or `.wfx` files. Use cube files for scalar-field rendering, not as substitutes for the underlying wavefunction when orbital composition, topology, or population analysis is required.

## Analysis Matrix

| Question | Primary analysis | Supporting analysis | Limit |
|---|---|---|---|
| Donor/acceptor regions | ESP extrema and area distribution | charges, local orbitals | ESP is surface-dependent |
| Frontier reactivity | HOMO/LUMO or SOMO/LUMO | orbital composition, Fukui | orbital energy alone is not kinetics |
| Charge transfer | NBO E(2), NPA, difference density | NTO for excitations | preserve fragment definitions |
| Bond weakening | bond length, frequency, WBI/Mayer | QTAIM BCP | no single descriptor is decisive |
| Noncovalent interaction | IGMH/IRI/NCI | QTAIM, interaction energy | colored surfaces are qualitative |
| Radical localization | spin density | alpha/beta orbitals, NPA spin | check spin contamination |
| Excited-state character | NTO and hole-electron analysis | transition density | track state identity |
| Aromatic shielding | ICSS/NICS tensor | current-density analysis | specify probe geometry |

## ESP and Surface Analysis

Map ESP on a declared electron-density surface, normally `ρ=0.001 a.u.`. Record:

- ESP minimum and maximum;
- position and chemical identity of extrema;
- positive/negative surface area;
- area-weighted mean and MPI;
- one common symmetric color scale and histogram bins for compared systems.

State the sign convention. Do not swap red/blue meanings between panels.

## Fukui Functions

Use consistent geometries and charge states:

- `f+` for susceptibility to nucleophilic attack;
- `f-` for susceptibility to electrophilic attack;
- `f0` for radical attack.

Report whether finite differences are vertical or relaxed and which population or real-space definition is used.

## Orbital and NTO Analysis

- Closed shell: HOMO, LUMO, and selected nearby orbitals.
- Open shell: alpha/beta channels, SOMO, and spin density.
- Keep isovalues identical within a comparison.
- Include orbital energies and fragment contributions when available.
- Use an orbital-manifold figure only when nearby orbitals affect the interpretation.

## NBO and Bond Orders

Record donor, acceptor, E(2), energy gap, Fock element, occupancy, and atom/fragment mapping. Compare values only under the same method and NBO definition. Treat Wiberg and Mayer indices as different descriptors.

## QTAIM

For each relevant critical point record atom pair, `ρ`, `∇²ρ`, `H`, `V`, `G`, and ellipticity. The absence of a bond critical point is not sufficient evidence that no interaction exists.

## IRI, IGMH, and NCI

Preserve:

- fragment definitions;
- isovalue;
- `sign(λ2)ρ` range;
- color convention;
- grid and downsampling;
- integrated or basin metrics when a quantitative comparison is claimed.

Use these surfaces to localize interactions. Use energies or topological/integrated descriptors to compare strength.

## Difference Density

Calculate complex and fragments at identical geometry, method, basis, and grid:

\[
\Delta\rho=\rho_{\mathrm{complex}}-\sum_i\rho_{\mathrm{fragment},i}
\]

Record fragment charge and multiplicity. A mismatched grid or relaxed fragment geometry invalidates direct subtraction.
