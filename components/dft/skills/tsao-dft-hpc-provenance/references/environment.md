# Environment Inspection

Inspect only named commands/modules and site paths. Record exact versions and module/container identifiers. Site-specific knowledge belongs in a local cluster guide, never hard-coded into a public Skill.

For environments with many compilers, engines and accelerator tools, use the deterministic parallel read-only inspector:

```bash
python skills/tsao-dft-hpc-provenance/scripts/inspect_execution_environment_parallel.py \
  --workers 0 \
  --out build/execution-environment.json
```

`--workers 0` selects a bounded automatic worker count. Results are merged in sorted identifier order, unavailable tools remain `NOT_AVAILABLE`, and the same privacy validator is applied. Parallel probing only reduces control-plane inspection latency; it is not DFT, GPU or performance evidence.
