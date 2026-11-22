# Contributing

## Development setup

```bash
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
python scripts/sync_version.py --check
python scripts/audit_repository.py
python -m pytest -q -p hypothesis.extra.pytestplugin
```

## Definition of done

A change is complete only when behavior, Schema, CLI, tests, documentation and generated evidence agree. New executable behavior requires positive, negative, boundary and tamper tests. Generated files must pass their `--check` mode and deterministic outputs must be byte-identical.

Tracked UTF-8 text uses LF line endings on every platform. The repository's
`.gitattributes` keeps fresh Windows checkouts consistent with the Unicode gate,
including when a contributor uses `core.autocrlf=true`; binary artifacts retain
their original bytes. The gate continues to reject CRLF and other encoding
defects instead of normalizing them during validation.

## Test evidence

The complete CI regression records raw JUnit and a matching event witness with
the existing `tsao_acceptance_pytest_events` plugin. After coverage, mutation and
performance artifacts are generated, consume both with
`python scripts/check_quality_baseline.py --junit-events artifacts/junit.xml.events.json`.
The plugin is loaded from `.github/acceptance` and requires an absolute
`--tsao-event-report` path that does not already exist.

Pytest may include passing subtests in the suite summary without adding separate
JUnit testcase elements. The quality record reports ordinary cases in `tests`,
with `subtests_passed`, `subtests_skipped` and `collection_skipped` separately.
Collector identity, lifecycle events, output paths and raw XML must agree.
Without event evidence, suite counts must agree with actual testcase elements;
subtest counts are never guessed. Actual failure or error nodes and malformed
mutation records cannot produce a passing quality record.

## Capability contracts

New capabilities require a unique slug, workflow, bounded inputs, explicit outputs, evidence policy, risk level, applicability boundary and completion gates. A named external engine is an integration target, not proof that it is installed or executed.

## Scientific claims

Do not fabricate citations, data, execution records or certainty. Distinguish observations, assumptions, model-dependent inference and causal claims. Material-specific trends require project evidence and uncertainty; they must not be encoded as universal rules.

## Compatibility and deprecation

Public CLI and schemas use semantic versioning. Additive compatible fields require tests and documentation. Breaking contract changes require a major release or a versioned parallel schema, migration guidance and an explicit deprecation period.

## Security and licensing

Never commit credentials, sensitive research material or copied code/prompts without compatible licensing and attribution. Keep actions pinned, dependencies bounded, archives safe and repository writes atomic. Follow `SECURITY.md` for private vulnerability reporting.

## Direct-main governance

This repository intentionally keeps only `main`. Do not create durable feature branches or pull requests for automated maintenance. A direct-main change must be narrowly scoped, tested before publication and followed by permanent CI. Never force-push.
