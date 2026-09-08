# Release process

1. Update `VERSION`, then run `python scripts/sync_version.py --write`.
2. Update `CHANGELOG.md` and quality thresholds only with an explicit rationale.
3. Run `python scripts/bump_version.py <version>` when a controlled version bump is required.
4. Run the complete local validation documented in `docs/VALIDATION.md`.
5. Push directly to `main`; permanent CI is read-only and idempotent.
6. Tag the validated commit as `v<version>`.
7. The release workflow re-runs all gates and publishes source ZIP, wheel, sdist, SBOM, validation evidence, engineering PDF, attestation and SHA-256 inventory.

Re-running CI or the manual audit never creates a repository commit. Re-running a tag release uploads assets with replacement semantics rather than creating a duplicate release.
