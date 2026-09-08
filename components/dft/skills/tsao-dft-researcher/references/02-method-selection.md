# Method selection and benchmarking

There is no universal functional/basis recipe. Choose a method because it
addresses the observable and system, not because a prior input happened to run.

## Decision dimensions

- main-group vs transition-metal/heavy-element chemistry;
- closed-shell vs open-shell, multireference risk and spin-state competition;
- covalent thermochemistry vs weak interactions vs long-range charge transfer;
- neutral vs anionic/diffuse electron density;
- gas, solution, explicit solvent, surface or condensed environment;
- geometry, frequency, barrier, spectrum, NMR, redox or real-space analysis;
- available benchmark and resource budget.

## Practical hierarchy

1. **Structure/conformer preparation:** sample conformers and electronic states
   before expensive DFT. A single hand-built geometry is not an ensemble.
2. **Opt/Freq level:** use one internally consistent level for geometry and
   Hessian. Include a defensible dispersion treatment when noncovalent contacts
   or conformational balance matter.
3. **High-level single point:** refine electronic energies on validated geometry
   when the accuracy target warrants it. Report the composite expression.
4. **Solvation:** use a documented continuum model; add explicit solvent for
   specific coordination, strong hydrogen bonding or proton shuttles.
5. **Benchmark:** compare a representative subset against experiment, a higher
   level or multiple defensible methods. Method agreement is evidence, not proof.

## Common method flags

- Anions, Rydberg states and diffuse charge often need diffuse basis functions.
- Long-range charge-transfer excitations often require range-separated TD-DFT
  and state-character checks.
- Heavy atoms may require ECP/relativistic treatment; never fabricate a GenECP
  block.
- Transition metals require explicit spin-state exploration and wavefunction
  stability checks.
- Very small energy differences should be interpreted against method,
  conformer, solvation and thermal uncertainties.

## Composite free energy

A common protocol is:

\[
G_{\mathrm{comp}}=E_{\mathrm{high}}+\left(G_{\mathrm{low}}-E_{\mathrm{low}}\right)
\]

All terms must correspond to the same geometry, charge and state. Record which
solvation and standard-state terms are already included to avoid double counting.
