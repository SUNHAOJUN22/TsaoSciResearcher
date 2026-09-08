# Architecture

## Eight-Skill DFT-first design

```text
tsao-dft-suite (root DFT orchestrator)
├── tsao-structure-prep
├── tsao-dft-researcher (molecular DFT, Gaussian/Multiwfn/VMD)
├── tsao-periodic-dft-materials (VASP/QE/CP2K)
├── tsao-dft-hpc-provenance
├── tsao-dft-ml-active-learning
├── tsao-dft-kinetics-multiscale
└── tsao-dft-catalysis-profile (optional, scoped)
```

The suite fixes the observable, model identity, support level, method fingerprint, task graph, resources and acceptance criteria. Engine Skills own input/output evidence. Downstream ML and kinetics consume accepted DFT artifacts.

## State and handoffs

Operational state belongs in `.research/`. Cross-Skill handoffs carry:

- project/task and source/target Skill IDs;
- structure/artifact IDs and SHA-256 hashes;
- accepted parent status;
- method fingerprint;
- engine support level;
- unresolved assumptions and blocking unknowns;
- requested outputs and success criteria;
- resource estimate and approval.

Release-layer research/figure manifests remain immutable evidence snapshots rather than live scheduler state.

## Support levels

1. `L0_REFERENCE` — documentation only.
2. `L1_HANDOFF` — structured manifest/handoff.
3. `L2_VALIDATED_ADAPTER` — deterministic preflight/parser/validator with tests.
4. `L3_EXECUTION_TESTED` — L2 plus real engine/version/site regression artifacts.

## Validation ladder

```text
planned → prepared → preflight passed → program completed
→ technically validated → scientifically accepted → claim accepted
```

No rung is inferred from the preceding rung. An optional domain profile may strengthen requirements but cannot weaken universal DFT gates.
