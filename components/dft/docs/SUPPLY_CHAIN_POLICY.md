# Supply-Chain Policy

## Deterministic blocking gate

Every `main` update must pass the offline quality gate on Python 3.10, 3.12 and 3.13. It validates dependency declarations, exact constraints, Agent eval contracts, capability claims, secret patterns, governed assets, local links, Ruff, mypy, Bandit, repository structure and all non-empty unittest suites.

GitHub Actions are pinned to complete commit SHAs. Workflow permissions are minimized per job. Dangerous write-capable triggers such as `pull_request_target`, `workflow_run`, issue comments or issue-triggered write jobs are prohibited.

## Dependency ranges and exact CI constraints

`requirements.txt`, `requirements-dev.txt` and `pyproject.toml` retain supported dependency ranges for the repository-style Skill collection. CI does not resolve those ranges afresh on every run: it installs against reviewed exact snapshots:

- `constraints/py310.txt`;
- `constraints/py312.txt`;
- `constraints/py313.txt`.

Each snapshot records the CPython version and source GitHub Actions run, uses exact pins, includes every direct dependency and excludes bootstrap packaging tools. `scripts/validate_constraints.py` rejects missing, duplicate, non-exact, incomplete or provenance-free snapshots.

Constraint refresh procedure:

1. trigger a reviewed temporary snapshot process from the current range declarations;
2. install and run `pip check` on every supported Python version;
3. capture sorted exact environments without `pip`, `setuptools` or `wheel`;
4. review the diff, vulnerability evidence and compatibility tests;
5. publish the three snapshots directly to `main`;
6. remove every temporary snapshot job or payload before restoring permanent CI;
7. require the full locked matrix, CodeQL, audits and SBOM to pass.

Hand editing transitive pins without resolver and CI evidence is prohibited.

## Network-dependent security evidence

The permanent supply-chain job checks:

- runtime dependency ranges with `pip-audit`;
- development dependency ranges with `pip-audit`;
- the exact Python 3.12 locked environment with `pip-audit --no-deps`;
- a CycloneDX JSON SBOM generated from the exact locked environment.

The workflow also runs CodeQL Python `security-extended`. All of these jobs run on pushes, pull requests, manual dispatch and a weekly schedule.

A service outage must be reported as `NOT VERIFIED` rather than transformed into a successful vulnerability result. A zero-vulnerability report means no matching advisories were returned for the resolved environment at that time; it does not prove that the dependency set contains no undiscovered vulnerability.

## Dependabot governance exception

`.github/dependabot.yml` records the `pip` and `github-actions` ecosystems, but `open-pull-requests-limit: 0` intentionally prevents automated update PRs because the repository owner requires a `main`-only, no-PR workflow. Dependency updates are reviewed and applied directly to `main` with complete CI evidence.

Dependabot alerts, secret scanning, push protection, CodeQL default setup and branch protection are repository settings. The audit GitHub App could not read those endpoints and records them as `NOT VERIFIED`; configuration must be confirmed by an administrator in the GitHub UI.

## Releases and provenance

Release snapshots should include:

- source archive and SHA-256;
- `VERSION`, `CITATION.cff` and `CHANGELOG.md` alignment;
- exact Python-version constraints;
- test and repository audit reports;
- CycloneDX SBOM;
- runtime, development and locked dependency-audit reports;
- exact GitHub Actions run and commit SHA;
- an honest list of real-engine/site and account-level capabilities that remain unverified.
