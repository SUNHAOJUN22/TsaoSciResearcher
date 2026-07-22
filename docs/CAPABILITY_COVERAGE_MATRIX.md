# AI for Science capability coverage

**Baseline:** uploaded 322-entry workbook and TsaoSciResearcher v0.5.2.

## Result

- **322/322 catalog slugs and names are represented as machine-readable v2 contracts.**
- 158 general research contracts remain compatible with the legacy catalog.
- 164 computation/engineering records now use their exact workbook names instead of generic numbered placeholders.
- 18 additional runtime/core contracts bring the v2 total to 340.
- External engines remain delegated integrations; a named contract is not an installed solver.

| Workbook category | Entries | Named contracts | Representation | Evidence |
|---|---:|---:|---|---|
| 科研Agent与编排 | 18 | 18 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| 文献与知识工程 | 18 | 18 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| 科研写作与出版 | 20 | 20 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| 数据统计与可视化 | 20 | 20 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| AI与机器学习科研 | 20 | 20 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| 生物信息与医学科研 | 18 | 18 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| 计算化学与材料计算 | 30 | 30 | Named delegated contracts + domain pack | `domain-packs/computational-chemistry-materials/`, `capabilities/v2/` |
| 分子动力学与多尺度 | 24 | 24 | Named delegated contracts + domain pack | `domain-packs/molecular-dynamics-multiscale/`, `capabilities/v2/` |
| 催化、高分子与复合材料 | 30 | 30 | Named delegated contracts + domain pack | `domain-packs/catalysis-polymers-composites/`, `capabilities/v2/` |
| 有限元与多物理场 | 20 | 20 | Named delegated contracts + domain pack | `domain-packs/fem-multiphysics/`, `capabilities/v2/` |
| CFD、颗粒与加工过程 | 18 | 18 | Named delegated contracts + domain pack | `domain-packs/cfd-particles-processing/`, `capabilities/v2/` |
| 化工流程、动力学与数字孪生 | 22 | 22 | Named delegated contracts + domain pack | `domain-packs/process-kinetics-digital-twin/`, `capabilities/v2/` |
| 实验室自动化与仪器 | 20 | 20 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |
| HPC、云计算与可重复性 | 20 | 20 | Named delegated contracts + domain pack | `domain-packs/hpc-reproducibility/`, `capabilities/v2/` |
| 科研管理、专利与诚信 | 24 | 24 | Named native/orchestrated/human-review contracts | `capability-index/`, `capabilities/v2/` |

## Scientific-computing engines

The workbook lists **32 engines** (for example GROMACS, LAMMPS, OpenFOAM, DOLFINx, DWSIM, IDAES, Quantum ESPRESSO and CP2K). They are not bundled. TsaoSciResearcher provides method selection, input review, convergence/UQ requirements, provenance and acceptance gates; actual execution belongs to TsaoSciComputation or another real solver/laboratory/HPC environment.

## Remaining boundaries, not defects

1. A capability contract does not install an external database, model, solver or instrument adapter.
2. Office output uses host-agent document tools; the core package does not embed a DOCX/PPT renderer.
3. Medical, safety, legal/FTO, research-integrity and final scientific acceptance decisions require qualified people.
4. Any future adapter that reuses upstream code must remain isolated and license-compatible.
