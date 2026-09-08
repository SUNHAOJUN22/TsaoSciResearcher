# Security Policy

## Supported version

Security fixes are applied to the current `main` branch and documented in `CHANGELOG.md`. Historical snapshots may not receive backports.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** interface when it is available. This creates a private vulnerability report. Do not place exploit details, credentials, private scientific data or licensed files in a public issue.

If private reporting is not available, open a minimal public issue titled `Security contact requested` without technical exploit details. A maintainer will establish a private channel.

Please include, when safe:

- affected commit and file paths;
- impact and realistic attack preconditions;
- a minimal reproduction using synthetic/non-sensitive data;
- whether secrets, destructive writes, prompt injection, unsafe parsing or supply-chain behavior are involved;
- suggested remediation, if known.

## Response targets

- acknowledgement: within 5 business days;
- initial severity and scope assessment: within 10 business days;
- coordinated remediation/disclosure plan: based on impact and exploitability.

These are response targets, not a guarantee. Confirmed issues are fixed without weakening tests, hiding findings or overstating scientific assurance.

## Scope

Security reports may cover Python code, installers, GitHub Actions, dependencies, Agent Skill routing, prompt injection, secret handling, destructive actions, artifact provenance and support-level escalation.

Scientific disagreement, convergence choices and unsupported feature requests are not security vulnerabilities unless they create a concrete integrity, confidentiality or availability risk.
