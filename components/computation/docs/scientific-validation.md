# Scientific reference validation

The deterministic scientific benchmark gate tests known analytical solutions, conservation laws, and invariants without claiming that an external solver is installed.

| Benchmark | Domain | Acceptance invariant |
|---|---|---|
| Steady one-dimensional conduction | Heat transfer | Finite-difference profile matches the linear analytical solution. |
| Hagen-Poiseuille pipe flow | CFD | Integrated parabolic profile matches analytical volumetric flow. |
| First-order CSTR | Reactor engineering | Steady mass-balance residual closes. |
| First-order PFR | Reactor engineering | RK4 integration matches exponential decay. |
| Harmonic oscillator | Molecular dynamics | Velocity-Verlet bounds total-energy drift. |
| Gaussian-chain second moment | Polymer statistical mechanics | Isotropic covariance trace equals `N b²`. |
| Parallel-plate capacitor | Electrostatics | Discrete electric field matches `V/d`. |
| Electrothermal balance | Multiphysics | Electrical input, Joule heating, and steady heat removal close. |

Run:

```bash
python scripts/run_scientific_benchmarks.py
```

The machine-readable result is `evidence/scientific-benchmarks.json`. Each record contains observed and expected values, absolute and relative error, tolerance, domain, and the invariant being checked.

These cases validate internal mathematics and physical invariants. They do **not** certify Gaussian, VASP, OpenFOAM, Aspen, GROMACS, another third-party solver, a commercial license, production HPC, plant controls, or user-supplied models and data.

## Result confidence

Reference benchmarks test internal analytical, conservation, and invariant behavior. Individual calculation results are separately assessed using the fail-closed [C0–C5 confidence model](scientific-confidence.md); benchmark success does not automatically raise a user result to any confidence level.

