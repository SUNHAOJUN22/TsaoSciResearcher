# Performance engineering

Performance changes are evidence-led and may not remove scientific, security, provenance, or acceptance gates.

The 3.0.1 architecture keeps the CLI import surface small, loads immutable JSON registries lazily through bounded caches, caps concurrent solver probes, avoids shell command construction, streams Manifests and release archives file-by-file, and keeps environment-dependent benchmarks separate from deterministic release acceptance.

## Recorded local baseline

`benchmarks/latest.json` is the machine-readable source of truth. The current snapshot measures orchestration overhead only—no scientific solver execution:

| Operation | Evidence source |
|---|---|
| CLI module import | `benchmarks/latest.json` |
| 164-capability registry cold load | `benchmarks/latest.json` |
| Capability registry cached access | `benchmarks/latest.json` |
| 27-adapter registry cold load | `benchmarks/latest.json` |
| 20-workflow registry cold load | `benchmarks/latest.json` |
| Route decision | `benchmarks/latest.json` |
| Conservative parser throughput | `benchmarks/latest.json` |

Values are environment-specific and are refreshed by `python scripts/verify_all.py --profile benchmark`. Regression decisions must compare like-for-like hardware, interpreter, filesystem, and input size. A faster number on different hardware is not evidence of a code improvement, and no result in this file is a solver benchmark.
