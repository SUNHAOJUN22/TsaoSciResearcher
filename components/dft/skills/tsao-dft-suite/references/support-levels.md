# Engine Support Levels

- `L0_REFERENCE`: science and boundary documentation only.
- `L1_HANDOFF`: machine-readable handoff or manifest generation.
- `L2_VALIDATED_ADAPTER`: deterministic input preflight/output parsing with tests.
- `L3_EXECUTION_TESTED`: L2 plus recorded regression on the real engine/version and environment.

Never infer a higher level from a README mention. `docs/ENGINE_SUPPORT_MATRIX.md` and `docs/CAPABILITY_STATUS.yaml` are authoritative release records.
