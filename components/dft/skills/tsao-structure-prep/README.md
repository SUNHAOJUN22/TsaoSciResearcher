# Tsao Structure Prep

General structure-preparation Skill for molecular and periodic DFT projects. It is suitable for molecules, organometallic complexes, crystals, surfaces, interfaces, defects and adsorption campaigns. It is not a geometry generator that silently decides chemistry.

```bash
python scripts/validate_structure_manifest.py examples/molecule-campaign/structure-manifest.yaml
python scripts/expand_structure_campaign.py examples/molecule-campaign/campaign.yaml --out candidates.csv
```

## Deterministic neighbor-search backends

`inspect_xyz.py` now consumes the governed `neighbor_list.py` numerical layer instead of requiring an unconditional all-pairs Python loop.

Available backends are:

- `python`: scalar all-pairs scientific reference;
- `numpy`: bounded-memory row-vectorized execution;
- `cell-list`: occupied-neighbor-cell candidate reduction;
- `auto`: NumPy for medium structures and cell-list for large structures.

All backends preserve deterministic zero-based pair identity and the same minimum-image definition. The cell-list contract supports non-periodic structures, orthogonal periodic boxes, triclinic boxes and partial periodic axes. Invalid shapes, non-finite coordinates, non-positive cutoffs, malformed periodic flags and singular boxes fail closed.

```bash
python scripts/inspect_xyz.py structure.xyz --backend cell-list --json

python scripts/inspect_xyz.py periodic.xyz \
  --backend cell-list \
  --periodic xyz \
  --box 10 0 0 0 10 0 0 0 10 \
  --json
```

The report records `pair_count` and `evaluated_pair_count`. A lower candidate count is an algorithmic observation only. It is not DFT-engine performance evidence, GPU qualification or a published speedup.

Native C++/OpenMP and CUDA/HIP/SYCL backends remain profile-, build- and equivalence-gated. They must consume this CPU reference contract rather than replace it. The repository-wide rules are defined in [`../../docs/ACCELERATION_ENGINEERING_DOCTRINE.md`](../../docs/ACCELERATION_ENGINEERING_DOCTRINE.md).

## v0.4 depth

See `SKILL.md`, `manifest.yaml`, `scripts/`, `templates/`, and `tests/` for the deterministic DFT adapters and scientific gates introduced in v0.4.0-alpha.1.
