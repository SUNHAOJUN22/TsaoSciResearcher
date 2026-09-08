# Deterministic Periodic-DFT Adapters

The included VASP, Quantum ESPRESSO and CP2K scripts perform input preflight and output evidence extraction. They are `L2_VALIDATED_ADAPTER` only for the fields exercised by repository tests; they are not full replacements for each engine's parser or manual.

- VASP: INCAR/POSCAR/KPOINTS and POTCAR TITEL mapping; OUTCAR energy/convergence/force/timing evidence.
- QE: pw.x namelists/cards/pseudopotential filenames; total energy, convergence, force, pressure and Fermi evidence.
- CP2K: Quickstep RUN_TYPE, basis/potential, grid, KIND, PBC and SCF checks; total energy and convergence evidence.

Every production site must record engine/version and run a site smoke/regression test before claiming `L3_EXECUTION_TESTED`.
