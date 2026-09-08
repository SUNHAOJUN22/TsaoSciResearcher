# Autonomous software hardening prompt

Use this prompt only for repository-local software engineering. It does not authorize external solver execution or scientific performance claims.

```text
Project: TsaoSciComputation.

Re-verify the sole authoritative main HEAD and permanent CI before changing anything. Treat prior commit, test, coverage, benchmark and artifact numbers only as clues. Preserve user changes and stop if the remote main moves while publication is being prepared.

Inspect the architecture, execution authorization boundary, solver-evidence model, tests, statement and branch coverage, controlled mutation evidence, static security checks, native C ABI, packaging, generated artifacts and source-bound manifests. Compare implementation patterns only against primary-source practices from mature scientific-computing and testing repositories.

Select the smallest high-value defect that can be reproduced without a third-party solver, commercial license, GPU/MPI qualification or fabricated scientific data. Fix the root cause. Add deterministic boundary, adversarial, status-matrix and regression tests. Make warnings, markers, xfail behavior and platform differences explicit. Update the matching JSON Schema, documentation, generated reports and manifest hashes.

Run the complete lint, formatting, type-checking, security, test, statement-coverage, branch-coverage, controlled-mutation, native, reproducible-source, reproducible-wheel, isolated-installation, SBOM and bounded benchmark gates. Treat generated-file drift and manifest drift as failures. Do not weaken a gate to make the change pass.

Keep a single main branch. Do not create a branch or pull request. Do not force-push. Publish only as a normal fast-forward update after every required gate passes. Remove any one-time qualification transport from the final product tree.

Keep external execution qualification at EXTERNAL_HOLD unless real evidence is supplied. Repository-local tests, analytical fixtures, hardware discovery and orchestration timings must not be represented as external solver correctness, GPU/MPI qualification or solver speedup.

When genuine external evidence arrives, qualify in this order:
1. identity, authorization and evidence integrity;
2. fixed-input CPU or trusted-reference correctness;
3. GPU/MPI numerical equivalence;
4. convergence, conservation and physical validation;
5. performance qualification using identical inputs and scientific settings.

Report exact modified files, test count, statement and branch coverage, controlled mutation result, native and package gates, final commit, permanent CI run and remaining external holds.
```
