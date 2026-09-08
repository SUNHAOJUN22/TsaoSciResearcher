# Type-Check Closure

Date: 2026-07-28  
Branch: `main`

## Scope

This closure addresses the isolated mypy findings exposed after the repository-wide security and supply-chain hardening.

The repaired targets are:

- `scripts/run_bandit.py`;
- `skills/tsao-dft-catalysis-profile/scripts/build_coordination_campaign.py`;
- `skills/tsao-dft-hpc-provenance/scripts/generate_job_array.py`;
- `skills/tsao-dft-kinetics-multiscale/scripts/validate_reaction_network.py`;
- `skills/tsao-dft-ml-active-learning/scripts/validate_dft_dataset.py`;
- `skills/tsao-dft-researcher/scripts/validate_figure_manifest.py`;
- `skills/tsao-dft-researcher/scripts/build_energy_profile.py`;
- `skills/tsao-periodic-dft-materials/scripts/preflight_vasp.py`;
- `skills/tsao-periodic-dft-materials/scripts/preflight_qe.py`.

## Repair rules

- no global mypy disable;
- no blanket `type: ignore` expansion;
- no weakening of runtime validation;
- no branch or pull request;
- type narrowing must follow actual runtime checks;
- scientific and security behavior must remain unchanged.

## Acceptance

This closure is accepted only when the permanent GitHub workflow passes on Python 3.10, 3.12 and 3.13, including Ruff, isolated mypy, Bandit, repository validation, all non-empty unit-test suites, dependency audits, SBOM generation and CodeQL analysis.
