# ResinDB compute, function-format and display-chain audit

Date: 2026-08-02

## 1. Scope

This audit covers the current production TypeScript surface, 26 Worker modules, data loading, compute utilities, worker hooks, scientific chart entry points, tests and CI gates. The machine-readable inventory is [`compute-module-catalog.json`](compute-module-catalog.json).

The audit is designed to answer four questions for every analytical function:

1. Is the mathematical definition explicit?
2. Is the input/output format explicit and finite?
3. Is there a Worker/hook/display route that can return or show the result?
4. Is the route covered by tests or a declared infrastructure boundary?

## 2. A-level findings — fixed in this pass

### A1. Data schema and TypeScript scalar mismatch

The prior JSON Schema allowed Boolean property values, while `PropertyValue` and most scientific/display code accepted only string or number. A Boolean could therefore pass repository schema review but fail or be misinterpreted downstream.

**Fix:** the canonical schema now allows only string or finite number; runtime and CI validators enforce the same contract.

### A2. Product schema did not require dates used by runtime types

`Product` required `createdAt` and `updatedAt`, but the JSON Schema did not. A malformed imported asset could pass schema validation and later break date-dependent UI or export logic.

**Fix:** both dates are required and validated as real ISO calendar dates.

### A3. Runtime product validation was too shallow

The runtime loader previously checked only a few top-level fields. It did not reject invalid property values, blank identifiers, duplicate categories, non-finite statistics or malformed dates.

**Fix:** `src/data/dataContract.ts` now provides a shared runtime contract aligned with repository schemas.

### A4. No single machine-readable map joined Worker, input, output and display contracts

Individual workers were tested, but no permanent gate proved that every Worker was inventoried and connected to a display surface.

**Fix:** the 26-module compute catalog and `npm run validate:compute` now enforce complete Worker inventory, file existence, chart mapping, test references and absence of explicit `any` in critical compute/data paths.

## 3. B-level findings — partly fixed, remaining work documented

### B1. Loose typing in import and quality-monitor paths

A small number of `any` annotations weakened compile-time protection for imported product updates and quality filters.

**Fix:** product updates are now generic over `keyof Product`; quality filter events and numeric parsing are explicitly typed.

### B2. Permissive numeric parsing

Quality and data-grid workers used prefix parsing, so a string such as `"12abc"` could be treated as the number `12` in numerical screening.

**Fix:** critical numerical paths now accept a string only when the entire trimmed value converts to a finite number.

### B3. Large compatibility components

`DataVisualizerLegacy.tsx` and several compatibility implementations remain large. They currently pass TypeScript, worker, browser and scientific UI validation, but their size increases review cost.

**Status:** non-blocking. Future migration should split one analytical surface at a time, preserving the current scientific-boundary wrappers and browser evidence.

### B4. Browser `alert()` remains in legacy interaction paths

Legacy analytical controls use native alerts for invalid input. This is visible rather than silent, but it is less testable and less accessible than structured inline errors or toasts.

**Status:** non-blocking. Replace incrementally with a typed validation-result component; do not suppress messages.

## 4. C-level improvements — completed

- README visual inventory reduced from 22 synthetic diagrams to 8 real CI-generated UI screenshots.
- Obsolete visual-bundle scripts and generated SVG inventory removed.
- README rewritten around data governance, scientific formulas, compute architecture, real UI evidence and validation.
- Permanent CI exact-source archive expanded to include `data/`, `docs/`, `README.md` and `SECURITY.md`.

## 5. Permanent acceptance gates

The repository must pass:

- canonical data-envelope and product validation;
- complete compute-surface catalog validation;
- scientific UI boundary validation;
- ESLint and strict TypeScript;
- complete regression, unit, scientific and Worker tests;
- whole-production-source coverage;
- build budget and external-data proof;
- HTTP and Chromium interaction smoke tests;
- production and complete dependency audits;
- deterministic exact-tree archive.

## 6. Scientific boundaries retained

This audit does not silently strengthen model claims:

- Spearman and dependency views remain association/sensitivity tools, not causal inference.
- Weibull remains a Bernard-rank linearized two-parameter estimate, not MLE.
- WLF remains a horizontal-shift model without fitted vertical shift.
- Sobol-named sensitivity currently uses seeded pseudorandom sampling, not a low-discrepancy Sobol sequence.
- Gaussian Process, Bayes and MOO outputs remain surrogate candidates requiring experimental review.
- KDE remains a density estimate, not a physical mechanism.
