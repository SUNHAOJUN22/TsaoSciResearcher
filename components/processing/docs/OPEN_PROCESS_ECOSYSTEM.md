# Open process-engineering ecosystem

TSAO treats simulation and analysis tools as interchangeable, qualification-bearing adapters to a canonical project data model.

## DWSIM and CAPE-OPEN

Use for open flowsheeting and interoperability. Record component identifiers, property package, unit-operation settings, convergence path, recycle initialization and DWSIM/CAPE-OPEN versions. Export stream and unit results into TSAO schemas and independently check mass, element and energy closure.

## IDAES

Use for equation-oriented process systems engineering, optimization, dynamic models and custom unit models. Pin IDAES, Pyomo and solver versions; record scaling, initialization, degrees of freedom, residual tolerances and property/reaction packages.

## Cantera

Use for gas/liquid/surface reaction mechanisms, reactors, flames and transport. Record mechanism provenance, phase definitions, thermodynamic polynomials, transport model, reactor formulation and sensitivity results. A mechanism that reproduces one condition is not automatically valid outside its calibration domain.

## Pyomo

Use for optimization, parameter estimation and decision models. Archive the mathematical formulation, units, bounds, objective, constraints, initialization, solver, termination condition, optimality gap and alternative-solution checks.

## CoolProp

Use for pure-fluid and selected-mixture thermophysical calculations within documented fluid and state ranges. Do not substitute it for polymer-solution, electrolyte, associating or reactive-equilibrium models without validation.

## Commercial simulators

Aspen, gPROMS and other commercial environments connect through software-neutral input/output contracts. Store configuration and exported results without making the proprietary file the sole source of truth. Reconcile balances and critical calculations independently.

## CFD, FEM, PBM and DEM

Declare geometry, mesh or population discretization, constitutive laws, boundary/initial conditions, numerical schemes, convergence, grid/time-step independence, validation targets and model-form uncertainty.

## FMI/FMUs and digital twins

An FMU must include variable definitions, units, causality, state/reset behaviour, solver expectations, valid operating envelope and versioned source-model provenance. Production deployment requires shadow validation, drift detection, cybersecurity review and rollback.

## Universal qualification checks

Every adapter output must pass applicable checks for conservation, dimensional consistency, known solutions, limiting behaviour, sensitivity, identifiability, uncertainty, applicability domain, independent recomputation and change impact.
