# Source parity and release identity

TSAO publishes two software artifacts and never treats them as interchangeable.

## Public source snapshot

- Source of truth: `main`.
- Manifest: `reports/SOURCE_CORE_MANIFEST.tsv`.
- Verification: `python -m tsao.cli doctor --root . --profile core`.
- Build: `python -m tsao.cli snapshot --root . --out TSAO-source.zip`.
- Purpose: reviewable open-source implementation, specialist contracts, tests and documentation.

## Qualified complete distribution

- Public reference: `reports/COMPLETE_DISTRIBUTION_REFERENCE.json`.
- Full manifest: `reports/COMPLETE_DISTRIBUTION_MANIFEST.tsv` inside the complete distribution.
- Internal integrity: `FILE_MANIFEST.tsv`, `checksums.sha256`, `SBOM.json`.
- Verification: `python -m tsao.cli doctor --root . --profile full` plus cleanroom extraction CI.
- Purpose: public source plus controlled inherited EPDM v9, SJTU-POE and universal-polymer assets and historical identities.

The public reference records the archive SHA-256, byte size, member count, test count, core hash and cleanroom result without pretending that controlled binary assets are ordinary Git source. The complete manifest retains per-file classification and does not change ownership or license.

## Technical approval

Neither software artifact approves chemistry, equipment, process safety, legal FTO, customer performance or a plant guarantee. Those states remain `NOT_EVALUATED` until project-specific evidence and named qualified approval exist.

Any missing path, duplicate path, unsafe path, size mismatch, SHA-256 mismatch, SBOM disagreement or false approval blocks qualification.
