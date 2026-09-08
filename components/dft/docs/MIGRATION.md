# Migration and Merge Record

## Sources merged

1. `SunHaojunComputationalChemistryResearcher v0.1.0-alpha.1` — Gaussian/Multiwfn/VMD execution skeleton, project state, parsers, figures and tests.
2. Local `computational-chemistry-research-visualization` — stricter evidence grades, calculation-artifact-claim validation, figure consistency and the DCS/MCSOMe/DMOS/Ti-TEA profile.
3. `AI_for_Science_最全Skill目录(3).xlsx` — indexed DFT/computational-chemistry, scientific-ML, HPC/provenance and multiscale-kinetics capability inventory.

## Consolidation decision

The catalog was consolidated into seven coherent Skills instead of dozens of shallow wrappers. Universal logic lives in reusable Skills. DCS/MCSOMe/DMOS, Si-O/Si-C, Ti/TEA, Ziegler-Natta and polyolefin-catalysis assumptions remain in an optional profile.

## Compatibility

- `tsao-dft-researcher` remains the entry point.
- Existing `.research/`, research-manifest and figure-manifest concepts remain compatible.
- New work may add structure, periodic, ML, HPC and kinetics manifests beside existing calculation files; raw files are never rewritten.
- Repository development remains `main` only.
