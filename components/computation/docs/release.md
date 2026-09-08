# Release governance

## Version authority

`VERSION` is the only authoritative release version. Package metadata reads it through `setuptools`, and runtime `tsao_computation.__version__` reads installed package metadata. README and `CITATION.cff` are synchronized and checked by `scripts/sync_version_metadata.py`.

A release is rejected when any of the following disagree:

- `VERSION`;
- Python package metadata;
- runtime `__version__`;
- English or Chinese README baseline;
- `CITATION.cff`;
- the current Changelog heading;
- the requested `vX.Y.Z` tag.

## Release gate

Formal releases are created only by `.github/workflows/release.yml` from the verified `main` commit. The workflow:

1. verifies that the requested tag equals `v$(cat VERSION)`;
2. checks version metadata consistency;
3. regenerates package assets, adapter/workflow documentation, examples, and the repository Manifest;
4. runs the complete deterministic `all` profile;
5. runs the observational benchmark separately;
6. builds byte-identical ZIP, tar.gz, and Wheel artifacts;
7. validates the Wheel in an isolated environment;
8. generates SPDX 2.3 and CycloneDX 1.6 SBOMs;
9. creates a release Manifest and SHA-256 checksum list;
10. creates an immutable annotated tag;
11. generates GitHub/Sigstore build-provenance and SBOM attestations;
12. publishes a GitHub Release with the complete evidence bundle.

No branch is created by the release process.

## Release assets

Each release contains:

- `TsaoSciComputation-X.Y.Z.zip`;
- `TsaoSciComputation-X.Y.Z.tar.gz`;
- the `tsao_scicomputation-X.Y.Z-*.whl` Wheel;
- `SOURCE_BUILD_REPORT.json`;
- `WHEEL_VERIFICATION.json`;
- `FINAL_VERIFICATION.json`;
- SPDX and CycloneDX SBOMs;
- `RELEASE_MANIFEST.json`;
- `SHA256SUMS`;
- provenance and SBOM Sigstore bundles.

The SBOM records the project, release artifacts, mandatory runtime dependencies, and optional validation/quality dependency groups. Runtime dependencies remain empty unless explicitly added to `pyproject.toml`.

## Consumer verification

After downloading all release assets:

```bash
sha256sum -c SHA256SUMS
gh attestation verify TsaoSciComputation-X.Y.Z.zip \
  --repo SUNHAOJUN22/TsaoSciComputation
gh attestation verify tsao_scicomputation-X.Y.Z-py3-none-any.whl \
  --repo SUNHAOJUN22/TsaoSciComputation
```

Checksum verification proves byte integrity against the release Manifest. Attestation verification binds the artifact digest to the repository, workflow, commit SHA, and GitHub/Sigstore signing identity. Neither mechanism alone proves that every scientific model or external solver is suitable for a user's application.

## Failure policy

The workflow must fail before tagging or publishing when quality, tests, security, mutation probes, packaging, SBOM generation, version consistency, or artifact integrity fails. Existing release tags and release assets are never overwritten. Corrections require a new patch version.

## Release checklist

- Changelog entry is complete and factual.
- Claim boundaries remain explicit.
- Security-sensitive changes include regression tests.
- `python scripts/verify_all.py --profile all` passes.
- `python scripts/verify_all.py --profile benchmark` completes and is interpreted as telemetry.
- `python scripts/sync_version_metadata.py --check` passes.
- Remote branches contain only `main`.
- The requested tag does not already exist.
- Release attestations and checksums are published and independently verifiable.
