# Supply-chain reproducibility

## Objective

TSAO separates dependency intent from an exact installation contract. `pyproject.toml` retains compatible version ranges for maintainability; `requirements.lock` records the resolved Python 3.11 development and runtime environment with exact versions and SHA-256 hashes.

## Fail-closed rules

The lock verifier rejects:

- any requirement not pinned with `==`;
- any package row without a SHA-256 hash;
- editable, VCS, local-file or direct-URL requirements;
- credential-bearing, insecure or unsupported package indexes;
- duplicate package names after PEP 503-style normalization;
- a lock that omits any runtime or `dev` direct dependency declared in `pyproject.toml`.

The permanent qualification workflow validates the committed lock, installs it with `pip --require-hashes`, installs TSAO with `--no-deps --no-build-isolation`, runs `pip check`, and executes the complete repository, Wheel and source-snapshot Gates. The lock also carries platform-conditional transitive packages required by the supported Windows runners, so hash mode does not delegate dependency resolution back to the network. The workflow does not currently claim an automated vulnerability scan; any future vulnerability report will remain software supply-chain evidence only, not scientific, engineering, HSE, customer or industrial approval.

## Regeneration

The permanent repository never keeps a lock-generation workflow. A one-shot workflow may generate and qualify the lock on `main`, commit the resulting lock and evidence, remove itself in the same final commit, and then delete obsolete branches after qualification passes.
