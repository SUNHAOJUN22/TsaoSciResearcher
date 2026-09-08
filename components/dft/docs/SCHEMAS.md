# Manifest Schemas

TsaoDFT uses small machine-readable contracts around immutable scientific files. Deterministic validators enforce semantic rules beyond lightweight YAML/JSON syntax.

## Root orchestration

- `tsao-dft-suite/templates/method-fingerprint.yaml`: molecular/periodic model chemistry, numerical settings, spin/charge, standard state and provenance.
- `tsao-dft-suite/templates/handoff.yaml`: cross-Skill artifacts, accepted parents, support level, unknowns, resources and approval.
- `tsao-dft-suite/templates/dft-project.yaml`: DFT-first project graph.

## Molecular DFT

- `research-manifest.json`: calculations → artifacts → claims;
- `figure-manifest.json`: artifacts → panels → comparison groups → outputs;
- `multiwfn-recipe.yaml`: semantic analysis, version, input hash, parameters and expected outputs;
- `uncertainty-budget.yaml`: model/method sensitivity components and combination/reporting policy.

## Structure preparation

The structure manifest records identity, source/hash, units, model type, charge/multiplicity candidates, transformations and review checks. Periodic models additionally record termination/defect, cell, vacuum, fixed-region, electrostatic/correction and periodic-image policies. Atom reordering is represented by an explicit mapping.

## Periodic DFT

The periodic project records engine/version/support level, structure hash, task type, method fingerprint, convergence studies, technical/scientific validation plan and task-specific model fields. Surface, adsorption, defect, NEB, phonon and electronic-property tasks have different parent/reference requirements.

## DFT-labelled ML

Dataset cards record independent sample unit, parent ID, structure/method/fidelity provenance, target units, split and exclusion policy. Model cards record train-only preprocessing, grouped split, features, seeds, metrics, uncertainty/calibration, applicability domain and interpretation status.

## HPC/provenance

HPC manifests record engine/version/support level, method fingerprint, scheduler, resources, environment, scratch, expected outputs, preflight/parser commands and approval. Site profiles contain no credentials. Restart-lineage manifests distinguish exact restart from geometry/wavefunction reuse.

## Kinetics/multiscale

Networks record phase/standard state, temperature, species composition/charge/site occupancy, accepted DFT artifacts, elementary reactions, barriers, reaction free energies, degeneracy and transition-state artifacts. External Cantera/CatMAP/Pyomo files remain review-required handoffs until downstream validation.
