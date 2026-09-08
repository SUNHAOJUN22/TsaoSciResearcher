# ResinDB Pro — Pass 9 finite aggregation hardening

## Scope / 范围

This pass closes the remaining production `Math.min(...array)` / `Math.max(...array)` argument-expansion paths identified in the acceptance audit. It does not change the physical meaning of Arrhenius, Weibull, Kissinger, Prony, polymer screening, or grade-comparison models.

本轮关闭验收审计中剩余的生产级数组展开极值路径，不改变 Arrhenius、Weibull、Kissinger、Prony、聚合物筛选或牌号比较模型的物理含义。

## Root cause / 根因

Variadic array extrema convert every array element into a function argument. For sufficiently large imported or generated datasets this can exceed the JavaScript engine argument limit and raise `RangeError`, even when all observations are numerically valid. Several call sites also created temporary mapped arrays only to recover min/max values.

## Implementation / 实现

- Added `src/lib/numericAggregation.ts`.
- `summarizeFinite()` performs count, min, max, compensated sum, and mean in one pass.
- Non-numeric, `NaN`, and infinite selector results are ignored explicitly.
- Neumaier compensation reduces cancellation error in mixed-magnitude sums.
- Comparison, Pivot, rheology screening, Arrhenius/Weibull charts, Kissinger kinetics, Prony initialization, and normalized comparison profiles use the shared contract.
- `validate:source` permanently rejects new variadic `Math.min(...` / `Math.max(...` production paths.

## Mathematical contract / 数理合同

For finite observations, the reducer maintains

```text
count, minimum, maximum, sum, compensation
```

with O(1) aggregation state. The final compensated sum is `sum + compensation`; the mean is `(sum + compensation) / count`.

## Regression / 回归

Dedicated unit coverage includes finite filtering, cancellation-prone `[1e16, 1, -1e16]`, no-finite-input behavior, and one million generated values. Formal delivery still requires the permanent main-branch CI to pass lint, typecheck, full tests, isolated science/worker tests, whole-source coverage, build, HTTP/Chromium smoke, dependency audits, sole-main proof, exact-tree, receipt, and PDF rendering.
