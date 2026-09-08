## Governance notice

The maintainer currently applies accepted changes directly to `main`. A pull request may be closed and reapplied as an audited main commit to preserve the repository's documented branch policy.

## Change evidence

- [ ] Scientific or engineering objective is stated.
- [ ] Affected Skills, support levels and evidence owners are identified.
- [ ] Tests fail before and pass after the change.
- [ ] `python scripts/quality_gate.py` passes.
- [ ] No test, threshold, security gate or scientific boundary was weakened.
- [ ] No secrets, proprietary data, licensed executables, POTCAR or restricted libraries are included.
- [ ] New third-party content has license and provenance information.
- [ ] Remaining `UNKNOWN` / `NOT VERIFIED` items are documented.

## Expected and forbidden behavior

Describe both the intended behavior and behavior the change must never permit.

## Evidence

Provide commit SHA, commands, logs, fixtures and any real-engine/site limitation.
