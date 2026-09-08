# Branch consolidation record — 2026-07-23

## Objective

Retain one authoritative branch, `main`, without losing useful work or allowing an older experimental line to regress the qualified alpha.6 tree.

## Branches reviewed

| Branch | Head | Ahead/behind at audit | Integration decision |
|---|---|---:|---|
| `agent/tsao-process-intelligence-os` | `a6648370622b24d5c156e967ef055c66550649ac` | +2 / -48 | Preserve unique utilities and tests; reject destructive alpha.5 removals; include history with an `ours` merge. |
| `dependabot/github_actions/actions/checkout-7.0.1` | `823eec34c4a94929ce85b9a69679c1e40adc873e` | +1 / -4 | Apply pinned `actions/checkout` v7.0.1 SHA to current CI; include history. |
| `dependabot/github_actions/actions/setup-python-7.0.0` | `c6ebe36c2053a857994fe2855ef8d1e96715fa08` | +1 / -4 | Apply pinned `actions/setup-python` v7.0.0 SHA to current CI; include history. |
| `dependabot/pip/pytest-gte-8.0-and-lt-10` | `e12c4dc6d4bd45da39b07f775210da6cbbf5e2d0` | +1 / -48 | Raise the tested pytest upper bound to `<10` in both dependency contracts; include history. |
| `dependabot/pip/setuptools-gte-68-and-lt-84` | `d2ddf832be785324da0d363ce1a1504191ff1a00` | +1 / -38 | Raise the setuptools upper bound to `<84` in build and development contracts; include history. |

## Preserved from the older alpha.5 experimental line

- `skills/poe/scripts/decode_matlab_gbk.py` — controlled conversion of UTF-8/GB18030/GBK historical MATLAB text to UTF-8.
- `skills/poe/scripts/inventory_corpus.py` — symlink-rejecting recursive corpus inventory with SHA-256, size, extension and MIME metadata.
- `skills/polymer-general/scripts/audit_evidence.py` — fail-closed evidence-ledger validation.
- regression tests for the three utilities and existing case-matrix/scale-up failure boundaries.

## Explicitly not reintroduced

The old experimental line deleted or weakened source manifests, provenance verification, process-package auditing, process-general workflows, universal-polymer tools and tests. Those removals were superseded by the current alpha.6 implementation and were not applied.

## Closure rule

Each reviewed branch is merged into `main` with Git history preserved while the already-integrated, qualified `main` tree remains authoritative. Branch deletion is allowed only after:

1. every branch head is an ancestor of the consolidated `main`;
2. repository tests, integrated CI, doctor, Ruff, dependency integrity and wheel build pass;
3. remote verification reports exactly one remaining branch named `main`.

## Final exact-ref recheck — 2026-07-26

The repository default branch is `main`. Every historical branch named above was queried again by its exact ref and returned `not found`, consistent with deletion after integration. No branch was created during the README, installed-Wheel or Python 3.14 convergence passes; all writes targeted the existing `main` branch.

The connector's free-text branch search does not reliably enumerate even `main`, so this record does not infer branch count from an empty search result. It relies on default-branch metadata plus exact-ref deletion checks for every previously known branch.

Scientific, engineering, safety, legal, customer and industrial approvals remain `NOT_EVALUATED`.
