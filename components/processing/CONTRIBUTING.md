# Contributing

1. Open an issue describing the decision problem and affected Gate, schema or subskill.
2. Work on a focused branch and preserve provenance and approval boundaries.
3. Add tests for every new scientific kernel, schema rule, migration or failure mode.
4. Never weaken or delete a failing test to obtain a green build.
5. Run `python -m pip install -e .[dev]` and `python scripts/run_ci.py`.
6. In the PR, state what changed, why, evidence used, uncertainty, backward compatibility and remaining external validation.

New professional modules should define decision question, scope, inputs, equations/algorithms, procedure, counterfactuals, uncertainty, failure modes, quantitative exit criteria, outputs, interfaces, external boundaries, sources and tests.
