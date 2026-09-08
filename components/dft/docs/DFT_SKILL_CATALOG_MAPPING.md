# DFT / Computational-Chemistry Skill Catalog Integration

Source reviewed: `AI_for_Science_最全Skill目录(3).xlsx` (SHA-256 `7c460d12faf16b63df33df5d00dda9576124369eb76adf638c7695a0d90a794e`).

The catalog was not copied blindly. Related entries were consolidated into reusable Skills so the repository does not expose dozens of shallow one-line wrappers.

| Repository Skill | Catalog coverage | Scientific boundary |
|---|---|---|
| `tsao-dft-suite` | S0001, S0002, S0006, S0013, S0014, S0015, S0016, S0017, S0028, S0029, S0030, S0031, S0320, S0321, S0322 | Cross-cutting DFT-first orchestration, support levels, handoffs and approval; does not duplicate engine execution. |
| `tsao-dft-researcher` | S0001, S0002, S0006, S0008, S0013, S0014, S0015, S0016, S0017, S0028, S0029, S0030, S0031, S0119, S0120, S0121, S0122, S0123, S0124, S0125, S0126, S0127, S0128, S0129, S0130, S0320, S0321, S0322 | Universal molecular DFT research control; Gaussian is the deepest executable adapter. |
| `tsao-structure-prep` | S0115, S0116, S0117, S0118, S0119, S0131, S0132, S0133, S0134, S0171, S0172 | Engine-neutral molecular/periodic model preparation; it does not decide chemistry silently. |
| `tsao-periodic-dft-materials` | S0131, S0132, S0133, S0134, S0135, S0136, S0137, S0138, S0139, S0140, S0141, S0142, S0143, S0144 | Periodic materials workflows for VASP/QE/CP2K handoffs, convergence and comparable-energy validation. |
| `tsao-dft-ml-active-learning` | S0080, S0081, S0082, S0083, S0084, S0085, S0086, S0087, S0088, S0089, S0090, S0091, S0092, S0093, S0094, S0095, S0096 | DFT descriptor ML, uncertainty and active learning; no correlated-conformer leakage. |
| `tsao-dft-hpc-provenance` | S0279, S0280, S0281, S0282, S0283, S0284, S0285, S0286, S0287, S0288, S0289, S0290, S0291, S0292, S0293, S0294, S0295, S0296, S0297, S0298 | HPC execution plans, provenance and recovery; submission remains approval-gated. |
| `tsao-dft-kinetics-multiscale` | S0168, S0173, S0174, S0175, S0176, S0177, S0178, S0185, S0186, S0190, S0191 | DFT free energies to TST/microkinetic/multiscale models; standard states and degeneracy are explicit. |
| `tsao-dft-catalysis-profile` | S0169, S0170, S0171, S0172, S0173, S0174, S0180, S0181, S0182, S0183, S0184 | Optional organometallic/polyolefin-catalysis profile; never auto-load for unrelated chemistry. |

## Scientific engines and libraries identified in the catalog

| ID | Engine/library | Role in TsaoDFT |
|---|---|---|
| E013 | Pyomo | Optimization |
| E015 | Cantera | Kinetics/Reactor |
| E016 | RMG-Py | Mechanism Generation |
| E017 | pymatgen | Materials Informatics |
| E018 | AiiDA | Workflow/Provenance |
| E019 | atomate2 | High-throughput DFT |
| E020 | ASE | Atomistic Workflow |
| E021 | Psi4 | Quantum Chemistry |
| E022 | Quantum ESPRESSO | Periodic DFT |
| E023 | CP2K | DFT/AIMD |
| E025 | MDAnalysis | MD Analysis |
| E029 | DeepChem | Scientific ML |
| E030 | RDKit | Cheminformatics |
| E031 | Snakemake | Workflow/HPC |
| E032 | Nextflow | Workflow/Cloud |

## Integration policy

- Existing upstream code is **not vendored**. Local documentation and scripts are original, and upstream licenses remain separate.
- Engine support is declared by level: deep adapter, validated handoff, manifest-only, or optional external analysis.
- Specialized assumptions live in profiles. The universal core never imports a catalyst, polymer, surface, force-field, U value or pseudopotential as an invisible default.
- `completed`, `validated`, and `accepted` remain distinct across every Skill.
