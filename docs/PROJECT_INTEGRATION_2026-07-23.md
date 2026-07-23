# Project integration audit - 2026-07-23

## Scope

This record documents the bounded integration of the project's accumulated scientific-research requirements into TsaoSciResearcher without creating a new branch.

## Integrated principles

The existing platform architecture already implements the appropriate general forms of the requested practices:

- evidence-first claim control and bidirectional citation traceability;
- explicit distinction between planned work, delegated execution and recorded execution evidence;
- measurement and applicability boundaries through workflow contracts, schemas and project-state gates;
- structure-property reasoning through configurable research-design and scientific-quality contracts rather than hard-coded material conclusions;
- causality guards that require mechanism, confounder, alternative-explanation and uncertainty checks;
- physical consistency, units, statistics, uncertainty and reproducibility checks;
- human approval for high-consequence scientific, safety, legal, medical and integrity decisions;
- deterministic HTML/SVG dashboards and a generated engineering PDF report;
- cross-platform CI, full regression, order-independence, static typing, security, mutation and bounded-performance gates.

## Domain adaptation rule

Polyolefin and cable-insulation experience is retained as a research-pattern example:

`processing history -> multiscale structure -> traps/charge transport -> macroscopic properties`

It must not be encoded as a universal conclusion. Material-specific numbers, phase assignments, trap interpretations and property trends require project evidence and remain subject to measurement boundaries, competing hypotheses and uncertainty.

## Closed-loop checks

The repository's permanent CI is the authoritative execution path. A push to `main` runs:

1. Python 3.10/3.13 Ubuntu, Python 3.12 Windows and macOS compatibility jobs;
2. schema, repository, structure, README-fact, dashboard, validation-evidence, research-quality-dashboard and engineering-report checks;
3. the full pytest regression suite and JUnit evidence export;
4. reverse-order and seeded-random-order regression;
5. Ruff formatting/lint, strict Mypy, Bandit and critical mutation checks;
6. bounded performance and byte-identical release packaging.

## Audit finding

At the start of this integration, `VERSION` and `pyproject.toml` declared release `0.5.3`, while the checked-in README headers and validation evidence still contained `0.5.2`. The repository already contains a main-branch finalization workflow intended to regenerate and align release documentation, dashboards, validation evidence, checksums and the engineering PDF after the complete gate set passes. This commit intentionally triggers that existing workflow instead of adding a duplicate branch or parallel reporting system.

## Non-claims

This integration record does not claim that an external experiment, literature search, DFT/MD/FEM/CFD/Aspen calculation or instrument run occurred. Software validation is not scientific acceptance of project-specific conclusions.
