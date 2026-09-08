# Phase 2K — Scientific UI, numerical-program and figure audit

## Exact baseline and scope

Phase 2K starts from the Phase 2J exact-tree baseline and reviews the production UI, chart layer, scientific workers, numerical compute layer, local evidence tools, tests, build budgets and CI. The implementation remains `main` only, FP64 only, and preserves the TypeScript reference backend and existing WASM fallback policy.

This phase does not claim that every legacy screen has been rewritten from scratch. Large, high-risk workspaces are retained through explicit compatibility wrappers so their existing controls and calculations remain available while the shared scientific figure layer and scientific-boundary notices are introduced. Those wrappers are enumerated by the machine-readable scientific UI audit.

## UI architecture update

A common `ScientificEChart` host now owns the ECharts lifecycle for migrated figures:

- one Canvas initialization path with `useDirtyRect`;
- one `ResizeObserver` path using `requestAnimationFrame` coalescing;
- reduced-motion support;
- ARIA labels and textual descriptions;
- consistent loading, empty and error states;
- three-times image export with an explicit light/dark background;
- stable chart sizing without re-creating an ECharts instance on each data update.

A versioned `scientific-figure-policy-1.0.0` applies restrained typography, color-vision-friendly palettes, axis formatting, logarithmic-axis defaults, tooltip containment, legends and export settings.

The Analytics view is reorganized as a scientific workspace with accessible tabs and a persistent statement that observations, model fits, proxies and rule-based scenarios must be interpreted separately.

## Scientific figure semantics

The following distinctions are now explicit in migrated figures:

- GPC and simple rheology curves derived from MFR or viscosity attributes are labelled as rule-generated proxies, not measured GPC or rheometry.
- Arrhenius, Weibull, RSM, Prony and kinetics figures draw observations and fitted model lines as separate visual layers.
- Weibull identifies Bernard median-rank ordinary least-squares linearization and states that it is not maximum-likelihood estimation.
- The RSM stationary point is not labelled as an optimum unless its Hessian/classification has actually established that conclusion.
- Feature importance is labelled standardized ridge-regression sensitivity attribution. Coefficient sign is conditional association direction, not causality or SHAP.
- Sobol/Jansen `ST−S1` is labelled aggregate higher-order contribution, not a pairwise interaction estimate.
- Gaussian-process observations, mean prediction, uncertainty band and expected-improvement candidate are separate layers.
- KDE and copula density maps use monotonic sequential palettes and identify the heatmap as a fitted model.
- SPC specification limits and `μ±3σ` distribution references are distinct.
- Model and proxy curves do not use decorative smoothing.

## Compatibility wrappers

The following very large modules remain available through explicit compatibility wrappers rather than being silently removed:

- `DataVisualizer`;
- `FormulaEditorModal`;
- `DependencyHeatmap`;
- `RheologyGraph`;
- `PredictiveTrends`;
- `MaterialTrendForecaster`;
- `ResinCapacityForecast`.

Each wrapper adds a visible scientific-boundary notice. The underlying legacy source is retained in a separately named `Legacy` module so functionality is not lost and future migrations can be performed one module at a time. These modules are not counted as completed common-lifecycle migrations by the scientific UI audit.

## Numerical-program review

The production scientific compute and worker paths were scanned for bare `Math.random()` and for reintroduction of explicit matrix inversion. Existing deterministic seeded sampling, QR/SVD least-squares, Cholesky solves, bounded nonlinear fitting, TypedArray transport and FP64 contracts remain in place.

No new numerical backend or speedup multiplier is claimed in this phase. The numerical corrections already accepted in prior phases remain authoritative. Phase 2K focuses on preventing the UI from overstating what those algorithms and input data establish.

## Machine-readable gate

`npm run validate:scientific-ui` writes `artifacts/scientific-ui-audit.json` and blocks CI when required figure policies or scientific-boundary labels disappear. It also records the compatibility wrappers instead of disguising them as completed migrations.

The final acceptance still requires documentation, source hygiene, governed data, the scientific UI gate, ESLint, TypeScript, complete regression tests, isolated unit and scientific-worker tests, whole-source coverage, production build, HTTP smoke, Chromium UI smoke, dependency audits, sole-`main` proof, deterministic exact-source-tree evidence, and rendered PDF validation.

## Remaining boundaries

- The compatibility-wrapped workspaces require later internal decomposition before they can use only the common chart lifecycle.
- Scenario pages still retain their previous calculators inside the compatibility layer; the new boundary notice prevents them from being presented as observed history or validated forecasts, but a later phase should replace their internal labels and bands directly.
- No second production WASM kernel is authorized.
- No fixed performance improvement is claimed without device-specific benchmark evidence.
