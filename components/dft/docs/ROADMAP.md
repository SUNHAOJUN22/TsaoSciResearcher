# DFT-Centred Roadmap

## Toward 0.4 beta

- real, license-safe regression fixtures produced on user-provided Gaussian/VASP/QE/CP2K installations;
- stronger final-geometry and task-specific periodic parsers;
- versioned Multiwfn menu execution and VMD/Tachyon image regression;
- method/basis/pseudopotential registry supplied by each laboratory;
- cross-platform CI and installation upgrade/rollback tests.

## Toward 0.5

- ORCA and Psi4 deterministic adapters;
- phonopy finite-displacement campaign adapter;
- Bader/LOBSTER/VASPKIT result validators without vendoring third-party software;
- uncertainty propagation across energy expressions and microkinetic models;
- accepted end-to-end molecular, periodic, ML and kinetics case studies.

The project will not expand by creating dozens of shallow software wrappers. New Skills or adapters must add concrete DFT knowledge, deterministic validation, provenance and tests.
