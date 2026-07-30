# First-Principles Computation Strategy Advisor

TsaoSciResearcher 0.7.0 adds a deterministic advisory layer that reasons from observables and governing physics to a minimum-sufficient computation or simulation hierarchy. It does **not** run DFT, MD, FEM, CFD, process simulators, or other solvers.

## Why this exists

Software-name-first recommendations are scientifically weak. A method must follow from the state variables that control the observable, the conserved quantities and symmetries, the thermodynamic or non-equilibrium setting, the relevant length/time/energy scales, and the evidence available for validation and falsification.

“First principles” is used in the broad scientific sense. Electronic-state problems may require quantum mechanics; free-energy problems require statistical ensembles and sampling; polymer morphology may require statistical field or mesoscale models; pressure-drop problems usually begin with conservation laws and constitutive rheology.

## Eight-stage reasoning chain

1. **Decision and observable** — define quantity, unit, tolerance, baseline, and decision threshold.
2. **Degrees of freedom** — identify electronic, molecular, field, population, structural, or internal variables that can change the observable.
3. **Exact constraints** — apply conservation laws, symmetry, stoichiometry, positivity, geometry, and admissibility.
4. **Physical frame** — select quantum, statistical-mechanical, thermodynamic, continuum, kinetic, or mixed physics.
5. **State and reservoirs** — select potential/ensemble and state equilibrium, metastability, ageing, or driven non-equilibrium.
6. **Scale analysis** — compare length, time, energy, correlation, relaxation, and forcing scales; use dimensionless groups where useful.
7. **Method ladder** — start from the lowest sufficient model, then define evidence-driven escalation.
8. **Validation and truth boundary** — define convergence, falsification, UQ, competing mechanisms, external execution, receipt, result review, and human acceptance.

## Supported strategy families

- electronic structure, defects, interfaces, and quantum states;
- reaction pathways, catalysis, transition states, and microkinetics;
- molecular thermodynamics, conformations, solvation, and free energy;
- polymer/soft-matter morphology, crystallisation, and phase separation;
- continuum flow, heat/mass transfer, and non-Newtonian transport;
- solid mechanics, viscoelasticity, fracture, and failure;
- charge transport, trapping, dielectric response, and breakdown;
- process kinetics, reactors, population balances, and distributions;
- mixed and multiscale questions with explicit bridge variables.

## CLI

```bash
python -m tsao_researcher strategy \
  "How do trap states and morphology control space charge and breakdown?" \
  --observable "space charge" \
  --observable "breakdown strength" \
  --condition "applied electric field" \
  --evidence "PEA charge profile" \
  --output strategy.json

python scripts/validate_computation_strategy.py strategy.json
```

The output is governed by `schemas/v2/computation-strategy.schema.json` and must state `solver_executed: false`.

## Method-selection rule

Start with the lowest-fidelity method that can causally determine the declared observable and be independently falsified. Escalate only when a failed validation identifies a missing degree of freedom, coupling, or scale. Do not interpret agreement with one dataset as proof of mechanism.

## External execution boundary

An approved strategy can be converted to a checksum-bound handoff. Execution, logs, outputs, convergence, and receipts remain external. TsaoSciResearcher then reviews the returned evidence and keeps `executed`, `checked`, `validated`, and `accepted` distinct.
