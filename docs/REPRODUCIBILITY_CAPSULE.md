# Reproducibility capsule

A capsule is a deterministic ZIP containing a manifest and checksum-addressed project files. Two exports from the same project state and environment are byte-identical.

## Modes

- `metadata`: project state, evidence, claims, protocols, receipts and provenance; raw `data/`, `figures/` and `artifacts/` directories are excluded.
- `full`: all regular project files within size and count limits.

## Safety and integrity

The exporter rejects symbolic links, path escape, oversized files and unsafe output paths. Verification checks duplicate members, ZIP link modes, expanded-size bounds, every file hash, the tree digest and deterministic capsule ID.

The capsule proves internal integrity and provenance. It does not prove that the scientific model, experiment or conclusion is correct.
