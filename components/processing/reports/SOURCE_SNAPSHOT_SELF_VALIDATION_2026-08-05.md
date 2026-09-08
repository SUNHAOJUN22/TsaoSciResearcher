# Source snapshot self-validation hardening — 2026-08-05

## Finding

The formally qualified Alpha.15 source ZIP (`ec8ac9d012c9aaeb4b07e3026a260b0617e43944b4b76776775d3826f2fbbede`) was deterministic, but an extracted copy did not pass its own repository tests without manual repair:

1. `reports/runtime/README.md` was excluded by the runtime-report prefix even though repository contracts require it;
2. `SOURCE_SNAPSHOT_IDENTITY.json` was generated after staging but was not classified as snapshot metadata by provenance verification.

## Root cause

Snapshot creation validated the checkout before staging and generated release metadata after staging, but it did not run provenance and release-metadata verification against the completed staged tree before compression.

## Remediation

- copy governed runtime support markers into the staged source tree;
- classify `SOURCE_SNAPSHOT_IDENTITY.json` as self-generated manifest metadata;
- verify staged provenance and release metadata before deterministic ZIP creation;
- expose machine-readable `self_validation` results;
- add extraction-level regression tests that verify the manifest, release metadata and runtime marker.

## Boundary

This closes a software release-integrity defect. It does not validate scientific parameters, process design, HSE, customer performance or industrial operation; those remain `NOT_EVALUATED`.
