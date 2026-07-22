# Capability coverage matrix

**Audit basis:** the user-provided 322-entry `AI_for_Science_最全Skill目录.xlsx`, the v0.5.1 source tree, `capability-index/`, `capabilities/v2/`, the seven domain packs, and GitHub Actions validation evidence dated 2026-07-22.

## Executive result

- External reference catalog: **322 named skills** across **15 top-level categories**.
- Exact slug-preserving coverage in the compatibility catalog: **158/322 (49.1%)**.
- Count-aligned domain capability slots: **164/322 (50.9%)** across seven computational/engineering categories.
- Additional runtime/core contracts not present in the workbook: **18**.
- Current v2 catalog total: **340 = 158 named research skills + 164 domain slots + 18 runtime/core capabilities**.

> The 164 domain records are real validated contracts, but their current slugs are generic domain-slot identifiers. They are **not** one-to-one named replicas of the 164 corresponding workbook skills. README wording must preserve this distinction.

## Category-level comparison

| Workbook category | Workbook entries | Exact named slugs in repo | Domain slots | Current representation | Evidence location |
|---|---:|---:|---:|---|---|
| 科研Agent与编排 | 18 | 18 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 文献与知识工程 | 18 | 18 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 科研写作与出版 | 20 | 20 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 数据统计与可视化 | 20 | 20 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| AI与机器学习科研 | 20 | 20 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 生物信息与医学科研 | 18 | 18 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 实验室自动化与仪器 | 20 | 20 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 科研管理、专利与诚信 | 24 | 24 | 0 | Exact named capability records retained from the workbook-derived compatibility layer | `capability-index/`, `capabilities/v2/` |
| 计算化学与材料计算 | 30 | 0 | 30 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/computational-chemistry-materials/`, `capabilities/v2/` |
| 分子动力学与多尺度 | 24 | 0 | 24 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/molecular-dynamics-multiscale/`, `capabilities/v2/` |
| 催化、高分子与复合材料 | 30 | 0 | 30 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/catalysis-polymers-composites/`, `capabilities/v2/` |
| 有限元与多物理场 | 20 | 0 | 20 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/fem-multiphysics/`, `capabilities/v2/` |
| CFD、颗粒与加工过程 | 18 | 0 | 18 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/cfd-particles-processing/`, `capabilities/v2/` |
| 化工流程、动力学与数字孪生 | 22 | 0 | 22 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/process-kinetics-digital-twin/`, `capabilities/v2/` |
| HPC、云计算与可重复性 | 20 | 0 | 20 | Count-aligned domain contracts; named workbook slugs are not preserved one-to-one | `domain-packs/hpc-reproducibility/`, `capabilities/v2/` |

## Scientific-computing engines

The workbook also lists **32 scientific-computing engines**. TsaoSciResearcher does not bundle or claim to execute those solvers. It models method selection, input review, convergence/uncertainty requirements, provenance and result acceptance through `computation-handoff`. Actual execution belongs to TsaoSciComputation or another real solver/laboratory/HPC environment.

## Priority gaps

1. Replace the 164 generic domain-slot slugs with one-to-one named domain contracts while preserving IDs and compatibility.
2. Add tested adapters/receipts for selected external engines; metadata alone is not an installed integration.
3. Expand laboratory automation from governance/SOP contracts to instrument-specific adapters in isolated packages.
4. Keep office-document production orchestrated through host tools; do not claim native DOCX/PPT rendering inside the core runtime.
5. Continue license review before importing any third-party implementation.

## Decision rule for public documentation

Public claims should say **340 validated capability records**, then disclose their composition. They should not say that all 322 workbook skills are individually implemented under their original names.
