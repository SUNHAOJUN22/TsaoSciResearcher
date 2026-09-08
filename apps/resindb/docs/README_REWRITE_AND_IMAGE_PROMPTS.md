# README Rewrite and AI Diagram Prompts

## 1. Master README rewrite prompt

```text
基于 ResinDB-Pro-by-SunHJ 当前 main 的实际代码、测试、计算模块与科学边界，重写 README.md 为中英双语验收版。必须覆盖：架构、数据层、材料统计、聚合物物理、LAMMPS 模板、ASTM/ISO 筛查、计算 Worker、验证链、命令行、典型工作流、部署策略、科学边界、验收工件。加入足量且与代码一致的数理程式，包括 Pearson/Student-t、线性回归、Spearman、置信区间、四分位数、偏度、峰度、KDE、PP 两相密度结晶度、工程应变、应力单位换算、相似度与推荐评分。中英文并列，不虚构实验认证、力场验证或跨设备性能保证。将 AI 技术示意图写入 docs/images/ 并在 README 中合理引用。更新后执行 lint、typecheck、test、build、Chromium、依赖审计与 exact-tree 验证；只保留 main，不创建新分支或 PR。
```

## 2. Image prompts

### Platform architecture

```text
Create a clean bilingual Chinese-English technical architecture infographic for ResinDB Pro. Show Data Layer → Scientific Compute → Application & UI → Validation Evidence. Include compact formula chips for Student-t correlation, centered regression slope, and LAMMPS atm-to-MPa stress conversion. Use a light background with navy, teal, and slate accents. No external logos.
```

### Material statistics and numerical robustness

```text
Create a bilingual technical infographic covering Pearson, Spearman, centered regression, Student-t confidence intervals, interpolated quartiles, adjusted skewness, excess kurtosis, finite-value filtering, one-pass bounds, radar percentile caching, and measured fixed-fixture performance. Clearly distinguish old failure modes from corrected contracts.
```

### Polymer physics and LAMMPS

```text
Create a bilingual technical infographic covering curated polymer repeat-unit inputs, rejection of ambiguous EPDM and unjustified tacticity/branching inference, PP-like two-phase-density crystallinity screening, LAMMPS initial box freezing, engineering strain, atm-to-MPa stress conversion, remap x, cooling parameters, timestep, and MSD group validation. State that screening and templates are not experimental or force-field certification.
```

### Delivery and validation

```text
Create a bilingual technical infographic showing governed validation scripts, lint/typecheck/tests/coverage, build and Chromium runtime proof, dependency audits, exact-tree and sole-main proof, PASS receipt, PDF, source archive, and evidence ZIP. Add README usage-strategy labels and acceptance metrics. Use the same clean vector visual system.
```

## 3. Provenance note

These images are conceptual AI-generated documentation aids. They are not runtime screenshots, benchmark evidence, experimental results, or scientific validation. Runtime UI evidence is stored separately under the `ui-*.png` inventory.
