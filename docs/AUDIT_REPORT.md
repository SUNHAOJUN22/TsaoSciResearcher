# Repository audit report

**Audit date:** 2026-07-14  
**Release:** v0.3.0  
**Scope:** uploaded design specification, uploaded 322-skill catalog, repository structure, executable checks and public README claims.

## Findings before remediation

The public `main` branch contained a polished README and root router, but core files referenced by them were absent, including the capability index, workflows, requirements and test runner. The advertised CI command therefore could not succeed.

## Remediation in v0.3.0

- Published the complete 158-capability research layer derived from the research-facing categories of the 322-skill catalog.
- Published all 15 workflows, 7 schemas, templates, references, deterministic validators and tests.
- Added CSV capability export, compliance mapping and repository-level audit.
- Added checks for README links, version consistency, capability references, workflow/router paths, CI targets, bytecode contamination and release metadata.
- Kept the README's capability boundaries explicit: native, orchestrated, delegated and human-reviewed.

## Objective limitations

- Metadata coverage is not equivalent to installed external tools.
- Automated integrity checks produce risk indicators, not misconduct findings.
- Medical, safety, legal and patent decisions require qualified human review.
- Real quantum chemistry, MD, FEM, CFD and process simulation execution belongs to TsaoSciComputation and actual solver environments.
