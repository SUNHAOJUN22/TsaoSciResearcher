# Security Policy

## Supported branch

Security fixes are developed directly against `main`. This repository is a research and demonstration application; it is not a certified production database, laboratory information management system, or regulatory decision engine.

## Reporting a vulnerability

Do not publish credentials, private datasets, exploit payloads, or personally identifiable information in a public issue. Contact the repository owner privately through GitHub before disclosing technical details. Include:

- affected commit and file path;
- reproduction steps with sanitized data;
- expected and actual behavior;
- impact assessment;
- a minimal remediation proposal, when available.

## Credential incident response

An API credential was previously committed in `.env`. Removing the file from the current tree does **not** invalidate the credential or erase it from Git history. The repository owner must:

1. revoke the exposed credential in the provider console immediately;
2. create a replacement credential with the minimum required API, origin and quota restrictions;
3. never commit `.env`, `.env.local`, service-account files, private keys or exported cloud credentials;
4. consider rewriting repository history only after coordinating with every collaborator and deployment;
5. review provider usage, access and billing logs for unauthorized activity.

## Frontend AI API configuration

Vite embeds every `VITE_*` variable into browser assets. A browser-delivered API key is therefore not a secret. `VITE_AI_API_KEY` and the in-app AI API Settings panel are intended only for restricted local-development credentials.

Production deployments should use an authenticated server-side gateway with:

- secret management;
- rate limiting;
- request and response validation;
- user-level authorization;
- audit logging;
- provider allow-lists;
- usage and cost controls.

## Formula execution boundary

User-defined formulas are parsed by a white-listed numeric grammar. Dynamic JavaScript execution (`eval` and `new Function`) is not permitted. Supported constructs are numeric literals, `Props['property']` references, arithmetic operators, parentheses, constants, and documented mathematical functions.

## Dependency response

Use `npm ci` for reproducible installation. Release CI runs both `npm audit --omit=dev --audit-level=high` and `npm audit --audit-level=high`; a high or critical advisory in either graph blocks release until the dependency is upgraded, removed, isolated with a verified non-applicability rationale, or replaced. The browser build does not claim an embedded Content Security Policy: production deployments must set and test CSP and other HTTP security headers at the hosting or gateway layer.

## Data and AI limitations

AI-generated properties and formulation suggestions are hypotheses, not manufacturer specifications, certified test results, safety determinations, or regulatory approvals. Validate outputs against traceable source data and laboratory methods before use.

## Browser session and local profile data

The built-in Viewer, Editor and Admin identities are demonstration roles only. Their session is stored in `sessionStorage`; no password is collected or persisted. Local avatars are restricted to browser-generated PNG, JPEG or WebP data URLs and should not contain sensitive images. Production identity and profile data require an authenticated backend.

## Data screening boundary

Range checks and generated PDF reports are screening aids, not certificates, laboratory reports or standards-conformity decisions. The application must not infer missing test methods, temperatures, loads or provenance.
