# Coverage matrix

This document traces the implemented repository against the user-provided `AI_for_Science_最全Skill目录(2).xlsx` and the TsaoSciComputation requirement specification. It is a coverage boundary, not a claim that every external solver is installed or live-tested.

## Catalog baseline

- Catalog entries: **322**.
- Computational subset: **164** entries across seven first-level categories.
- Scientific-computing engine shortlist: **32** rows.
- Repository baseline: **164** canonical capabilities, **20** workflows, and **27 core adapters**.

The two sets of 164 are equal in size but are not a one-to-one slug copy. The repository reorganizes the catalog into explicit scale selection, solver-independent scientific contracts, validation gates, multiscale handoffs, and bounded HPC recovery.

## Capability-domain mapping

| Catalog category | Catalog count | Repository workflow coverage |
|---|---:|---|
| 计算化学与材料计算 | 30 | scale-selection, quantum-chemistry, periodic-dft, reaction-path |
| 分子动力学与多尺度 | 24 | molecular-dynamics, enhanced-sampling, machine-learning-potential, multiscale-coupling |
| 催化、高分子与复合材料 | 30 | catalysis, polymerization, polymer-composite |
| 有限元与多物理场 | 20 | finite-element, multiphysics |
| CFD、颗粒与加工过程 | 18 | cfd, extrusion |
| 化工流程、动力学与数字孪生 | 22 | process-simulation, reactor-engineering, dynamic-control, digital-twin |
| HPC、云计算与可重复性 | 20 | hpc-execution plus cross-cutting provenance, CI, packaging, and failure gates |

Use `capability-index/README.md` for the authoritative 164 capability IDs and slugs.

## Engine shortlist coverage

The 32-row engine shortlist maps to the adapter registry as follows.

### Direct or combined core-adapter coverage

- DOLFINx/FEniCS → `dolfinx`
- MOOSE → `moose`
- Kratos → `kratos`
- Elmer → `elmer`
- SU2 → `su2`
- OpenFOAM → `openfoam`
- DWSIM → `dwsim`
- IDAES and Pyomo → combined `idaes-pyomo`
- OpenModelica → `openmodelica`
- Cantera and RMG-Py → combined `cantera-rmg`
- ASE and pymatgen → combined `ase-pymatgen`
- Psi4 → `psi4`
- Quantum ESPRESSO → `quantum-espresso`
- CP2K → `cp2k`
- OpenMM → `openmm`
- GROMACS → `gromacs`
- PLUMED → `plumed`
- LAMMPS → `lammps`

### Catalog engines without a standalone adapter

The following **11 catalog engines** are not represented as independent executable adapters: MFEM, deal.II, SfePy, OpenSees, AiiDA, atomate2, MDAnalysis, DeepChem, RDKit, Snakemake, and Nextflow.

They may be referenced in method planning or lawful handoff guidance, but the repository must not claim environment probing, native input generation, native parsing, or live execution for them until a dedicated adapter and tests are added.

### Additional repository adapters

The repository also includes core adapters not present as separate rows in the 32-engine shortlist: Gaussian, ORCA, PySCF, VASP, ABACUS, GPAW, MACE, and Aspen Plus/Dynamics/ACM.

## Acceptance boundary

- Adapter presence is not solver availability.
- `live_execution_verified` remains false for every external solver adapter.
- Commercial adapters require a user-supplied lawful installation and license.
- Combined adapters do not imply every component is installed.
- Missing standalone adapters are explicit known limits, not silently emulated capabilities.
- Scientific acceptance remains fail-closed and requires convergence, physical validation, uncertainty, applicability, provenance, and required human approval.
