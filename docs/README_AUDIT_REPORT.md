# Bilingual README audit report

**Audit date:** 2026-07-22  
**Release audited:** v0.5.1  
**Scope:** current `main` source, executable CLI/installers, 15 workflows, 15 schemas, capability catalogs, domain packs, tests, GitHub Actions evidence, the uploaded design specification and the uploaded 322-skill workbook.

## Method

The audit used code and generated artifacts as the source of truth:

1. parsed `VERSION`, `manifest.json`, `pyproject.toml`, capability indexes and workflow/schema inventories;
2. read the actual CLI parsers and installer path mapping;
3. compared all 322 workbook slugs against the 340-record v2 catalog;
4. read GitHub Actions JUnit, mutation and performance artifacts;
5. checked public README claims against the implementation and scientific-execution boundaries.

## Findings before this rewrite

| Finding | Risk | Resolution |
|---|---|---|
| `README.md` was primarily Chinese while `pyproject.toml` used it as the canonical package page | International users received an incomplete project entry point | Replaced it with a complete English canonical README and retained a full Chinese edition |
| `README.zh-CN.md` was only a short redirect/summary | Chinese users did not receive a complete standalone manual | Rewritten as a full Chinese README |
| `README_EN.md` was a short summary rather than a mirror | Three README files could drift | It is now byte-identical to `README.md` and checked in tests |
| “340 capabilities” was not decomposed | Could be read as 340 individually named workbook skills | Now disclosed as 158 named research capabilities + 164 domain slots + 18 runtime/core capabilities |
| No explicit 322-skill comparison existed | Coverage could not be independently understood | Added `docs/CAPABILITY_COVERAGE_MATRIX.md` |
| Performance design was described without the verified release measurements | Readers could not distinguish architecture claims from measured results | Added actual GitHub Actions smoke metrics with platform and threshold caveats |
| CI descriptions were spread across README and validation docs | Evidence could become stale | Added `docs/VALIDATION_EVIDENCE.json` and machine-generated `docs/README_FACTS.json` |
| README facts were handwritten | Counts could silently drift after code changes | Added `scripts/build_readme_facts.py --check` and regression tests |

## Verified implementation facts

- Version: **0.5.1**
- v2 capability records: **340**
- Composition: **158 named compatibility capabilities + 164 domain slots + 18 runtime/core capabilities**
- Workflows: **15**
- JSON Schemas: **15**
- Domain packs: **7**
- Reference files: **22**
- Templates: **13**
- Test modules before this documentation test was added: **18**
- GitHub Actions full regression: **96 tests, 0 failures, 0 errors, 0 skipped**
- Critical mutation smoke: **15/15 killed**
- Compatibility matrix: Ubuntu/Python 3.10 and 3.13, Windows/Python 3.12, macOS/Python 3.12

## README changes

The rewritten bilingual documentation now:

- distinguishes native runtime behavior, tool-orchestrated work, external execution and qualified-human decisions;
- documents every CLI subcommand that actually exists;
- documents all installer agents/scopes and their real target paths;
- gives a complete lifecycle and state model without equating `completed`, `checked`, `validated` and `accepted`;
- makes computation handoff boundaries explicit;
- exposes the exact capability-composition limitation;
- reports measured performance only with environment and threshold context;
- links design-to-code, capability coverage and validation evidence.

## Residual limitations

1. The 164 domain slots are count-aligned but not one-to-one named implementations of the 164 computational workbook skills.
2. External databases, instruments and solvers are not bundled.
3. Research retrieval, plotting and office-document production depend on tools available to the host agent.
4. Software checks validate contracts and implementation behavior; they do not scientifically accept a calculation, experiment or manuscript.
5. The GitHub Actions evidence is a dated release record, not a promise that every future commit remains green.

## Maintenance rule

Any change to capability counts, workflows, schemas, domain packs or README structure must run:

```bash
python scripts/build_readme_facts.py --write
python scripts/build_readme_facts.py --check
python scripts/generate_checksums.py --write
python scripts/audit_repository.py
```
