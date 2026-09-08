# Security Policy

## Supported versions

| Version | Security support |
|---|---|
| 3.0.x | Supported |
| 2.x and earlier | Unsupported; upgrade before requesting a fix |

Security fixes are released from the canonical `main` line. Historical tags remain immutable.

## Report a vulnerability privately

First open the repository **Security** tab. When **Report a vulnerability** is available, use that private, structured reporting form. Do not disclose a suspected vulnerability in a public issue, pull request, discussion, benchmark log, or example dataset.

If GitHub does not display the private-reporting button, use a non-public contact route listed on the repository owner's GitHub profile and identify the message as a TsaoSciComputation security report. Do not put exploit details in a public contact form. Maintainers with repository access should create a draft repository security advisory instead of a public issue.

Include only the minimum information needed to reproduce and assess the report:

- affected version or commit;
- affected command, contract, adapter, workflow, or artifact;
- reproducible steps and expected versus observed behavior;
- security impact and realistic attack conditions;
- suggested mitigation, when known.

Do not attach credentials, license files, proprietary solver inputs, private datasets, production DCS/SIS exports, or regulated information. Use synthetic or redacted fixtures whenever possible.

## Triage and disclosure

The maintainer will validate scope, severity, and reproducibility before deciding whether the issue is a code defect, unsafe configuration, unsupported environment, or scientific-model limitation. Confirmed vulnerabilities are fixed on `main`, exercised by regression tests, and documented in the changelog before coordinated public disclosure.

A security report is not considered resolved merely because a process exits successfully. Fix acceptance requires the relevant path, execution, parsing, state, provenance, packaging, or scientific-validation invariant to pass its fail-closed tests.

## Security invariants

- Paths are confined to declared roots and symbolic-link escapes are rejected.
- Subprocesses use argument vectors, `shell=False`, bounded timeouts, and controlled environments.
- Archives are hash-bound, size-bounded, and safely extracted.
- Unknown, incomplete, failed, or abnormal output is not promoted to convergence or validation.
- Credentials, licenses, proprietary solver files, secrets, and private datasets are never bundled.
- Installed Skill copies are checked against the complete SHA-256 Manifest.
- Release archives and Wheels are reproducible, checksummed, SBOM-described, and provenance-attested.
- Automation never writes to DCS/SIS, disables safeguards, or bypasses required human approval.

## Good-faith research

Good-faith testing must avoid privacy violations, destructive testing, service disruption, persistence, social engineering, and access to data beyond what is necessary to demonstrate the issue. Stop testing once sufficient evidence has been collected and report privately.

## Scientific safety boundary

This repository validates orchestration, contracts, deterministic fixtures, parsers, security controls, packaging, and isolated installation. It does not certify third-party solvers, commercial licenses, production HPC environments, plant control systems, or the scientific validity of user-supplied models and data. High-risk reactor, control, digital-twin, runaway, safety, and commercial-handoff decisions require qualified domain review.
