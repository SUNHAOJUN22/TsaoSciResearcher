# Dependency maintenance

## Branchless upstream policy

The canonical upstream repository intentionally retains only `main`. Automated version-update pull requests create update branches, so upstream dependency maintenance uses a branchless scheduled audit instead. External contributors may still use branches in their own forks.

## Weekly audit

`.github/workflows/dependency-audit.yml` installs the declared validation, quality, and security dependency groups in an isolated GitHub-hosted Python 3.13 environment and runs the pinned `pip-audit` toolchain. It has read-only repository permissions, never changes source, never opens a branch, and uploads both the JSON vulnerability report and the resolved environment snapshot.

A failed audit is an investigation signal, not permission to blindly upgrade. Review the advisory, exploitability, affected execution path, fixed versions, upstream release notes, and compatibility before updating constraints or minimum versions on `main`.

## Update procedure

1. Review the scheduled audit artifact and upstream advisories.
2. Change only necessary dependency declarations on `main`.
3. Run `python scripts/verify_all.py --profile all` and the branchless dependency audit.
4. Preserve fail-closed tests and scientific claim boundaries.
5. Record the decision in `CHANGELOG.md`; issue a patch release when user-visible or security-relevant behavior changes.

`pip-audit` detects known Python-package vulnerabilities; it is not a static analyzer, malicious-package detector, solver validator, or substitute for CodeQL, Bandit, repository security invariants, SBOMs, provenance attestations, and qualified scientific review.
