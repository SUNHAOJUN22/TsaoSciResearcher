# TSAO-PROCESSING-SKILL — Final Debug Closure

## Code changes

The public-distribution boundary now has one registry scanner and one classifier:

```text
source_asset_registry.json + declared parts
                 │
                 ▼
        _scan_registry(...)
          ├── safe part validation
          ├── duplicate-key/non-finite JSON rejection
          ├── record counting and optional stable-ID checks
          ├── one controlled-record classifier
          └── manifest, part-set and corpus digests
                 │
          ┌──────┴───────────────────┐
          ▼                          ▼
audit_public_distribution   evaluate_public_distribution
(repository/package guard)  (surface-aware CLI policy)
```

`scripts/check_public_distribution_policy.py` remains a compatibility adapter only. It contains no independent JSON parser, classification vocabulary, digest logic, decision parser, or release verdict.

## Regression contract

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_distribution_containment_v20.py \
  tests/test_distribution_policy_single_source.py \
  tests/test_release_integrity_alpha6.py \
  tests/test_main_only_ci_policy.py \
  tests/test_public_distribution_boundary_workflow.py
python scripts/run_ci.py
```

The single-source regression binds both public APIs to the same manifest digest, part-set digest, record count, controlled-record count, and part count. It also rejects the previous `_policy_*` duplicate classifier path.

## Distribution boundary

```text
PUBLIC_WHEEL            = BLOCKED_CONTROLLED_METADATA_CLASSIFICATION
PUBLIC_SDIST            = BLOCKED_CONTROLLED_METADATA_CLASSIFICATION
PUBLIC_SOURCE_SNAPSHOT  = BLOCKED_CONTROLLED_METADATA_CLASSIFICATION
```

This fail-closed result is intentional while tracked registry records remain classified as controlled. Refactoring and software tests do not reclassify metadata and do not establish scientific, engineering, HSE, customer, legal, IP, or industrial approval.
