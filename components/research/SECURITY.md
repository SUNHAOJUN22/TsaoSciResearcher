# Security policy

## Supported versions

Security fixes are provided for the latest tagged release and the current `main` branch. Older versions may receive guidance but are not guaranteed a backport.

## Private reporting

Do not disclose a suspected vulnerability in a public issue. Contact the repository owner privately through GitHub and include the affected version, reproduction steps, impact, prerequisite access and any safe proof of concept. Do not include real credentials, patient-identifiable data, unpublished manuscripts or proprietary datasets.

## Response targets

- acknowledgement: normally within 3 business days;
- initial severity and reproduction assessment: normally within 7 business days;
- remediation plan: based on exploitability, data exposure and scientific-integrity impact.

These are operational targets, not contractual guarantees.

## Security boundaries

- External solvers, instruments, databases and HPC environments are outside this repository's trust boundary.
- A computation handoff is not authorization to execute.
- An execution receipt is accepted only as provenance evidence and is checksum-verified; it does not prove scientific validity.
- Paths are contained, archives are bounded, symbolic links are rejected and writes use atomic replacement where supported.
- GitHub Actions are pinned to immutable commit SHAs; workflows with write permission are limited to branch governance and tag release.

## Sensitive research data

Classify data before use. Keep secrets and regulated or contract-restricted data outside the repository. Metadata capsules should be preferred when raw data cannot be redistributed. External uploads require explicit user authorization and applicable institutional approval.
