# MDAnalysis trajectory extension

This route analyzes a validated trajectory/topology pair and remains separate
from static quantum-chemistry evidence.

## Pre-analysis

- identify topology and coordinate units;
- unwrap periodic molecules and center the system as needed;
- align on a declared atom selection;
- identify equilibration and production windows;
- record frame stride and effective sampling.

## Common analyses

- RMSD and RMSF with explicit reference and selection;
- distances, angles, contacts and hydrogen-bond occupancy;
- radial distribution functions and coordination numbers;
- clustering and representative structures;
- density profiles and spatial distributions;
- block-averaged observables and uncertainty.

## Validation

Inspect time series, multiple blocks/replicas and sensitivity to alignment,
cutoffs and selection language. Do not report thousands of correlated frames as
thousands of independent replicates. For QM/MM or snapshot DFT, record how frames
were selected and whether solvent/environment was retained.
