# Contributing

## Canonical repository policy

The upstream repository keeps **`main` as its only remote branch**. Do not create long-lived or temporary feature branches in `SUNHAOJUN22/TsaoSciComputation`.

External contributors should:

1. fork the repository;
2. create a short-lived branch in their own fork;
3. submit a pull request from the fork to upstream `main`;
4. delete the fork branch after validated integration.

Repository maintainers may commit directly to upstream `main` only when the intended file scope is understood and the complete verification gates are run before the change is declared complete. Tags are immutable release records, not development branches.

## Required change content

Every behavior change must include the relevant combination of:

- calculation, result, or handoff contract updates;
- positive, negative, malformed-input, and failure-path tests;
- scientific assumptions, units, reference states, convergence criteria, uncertainty, and applicability boundaries;
- adapter metadata, fixtures, parser policies, and explicit unsupported behavior;
- security and provenance implications;
- English and Chinese user-facing documentation when public behavior changes.

Never claim live solver execution unless the exact solver version, environment, lawful license state, fixture hashes, and observed results are recorded. Adapter presence is not proof of solver availability.

## Required verification

Install the controlled validation toolchain and run:

```bash
python -m pip install -e '.[validation,quality]'
python scripts/verify_all.py --profile all
python scripts/verify_all.py --profile benchmark
```

`all` is the deterministic release gate. It covers quality, tests and coverage, repository and Schema validation, generated assets, Manifest integrity, security scanning, controlled mutation probes, reproducible source archives, reproducible Wheel construction, isolated Wheel installation, SBOM generation, and release checksums. Benchmark results are observational and must not be confused with deterministic correctness.

Do not weaken thresholds, delete negative tests, broaden exception handling, suppress security findings, or rewrite evidence merely to make CI green.

## Dependency maintenance

The upstream repository does not enable Dependabot version-update pull requests because they create update branches. Review the read-only weekly dependency-audit artifact, make reviewed changes directly on `main`, run every deterministic gate, and issue a patch release for security-relevant or user-visible changes. See `docs/dependency-maintenance.md`.

## Version and release changes

`VERSION` is the only authoritative version source. Run:

```bash
python scripts/sync_version_metadata.py --release-date YYYY-MM-DD
python scripts/sync_version_metadata.py --check
```

A formal release must use the protected Release workflow, pass all gates, create an immutable `vX.Y.Z` tag, publish reproducible archives and Wheel artifacts, attach SPDX and CycloneDX SBOMs, publish SHA-256 checksums, and generate GitHub/Sigstore provenance attestations.

## Scientific review boundary

Reviewers should distinguish software correctness from scientific validity. A parser can be correct while a model is unsuitable; a converged numerical run can still violate conservation, reference-state, uncertainty, or applicability requirements. High-risk conclusions require qualified domain review and explicit human approval.
