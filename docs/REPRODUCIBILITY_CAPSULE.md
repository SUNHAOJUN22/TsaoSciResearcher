# Reproducibility capsule

A capsule is a deterministic ZIP containing a manifest and checksum-addressed project files. Two exports from the same project state and environment are byte-identical.

## Modes

- `metadata`: project state, evidence, claims, protocols, receipts and provenance; raw `data/`, `figures/` and `artifacts/` directories are excluded.
- `full`: all regular project files within size and count limits.

## Safety and integrity

The exporter rejects symbolic links, path escape, oversized files and unsafe output paths. Verification checks duplicate members, ZIP link modes, expanded-size bounds, every file hash, the tree digest and deterministic capsule ID.

The ZIP and its `.sha256` sidecar must be outside the managed `.tsao-research/`
directory, for example `project-full.zip` beside that directory. Exporting inside
managed state is rejected even for a new path: it could replace project metadata,
research inputs or a registered handoff, and would feed generated output back into
later snapshots. Re-exporting to the same external ZIP remains supported and is
byte-identical when project state and environment have not changed.

Snapshot verification, file reads and publication hold the same project mutation
lock as handoff and receipt updates. Project writers must honor that lock; direct
filesystem edits that ignore it are outside this consistency guarantee. Both
output paths are checked before publication, including the sidecar's path components.

ZIP 及 `.sha256` 校验文件必须放在受管理的 `.tsao-research/` 目录之外，例如与该目录并列的
`project-full.zip`。目录内部的新路径同样会被拒绝，避免覆盖原件或将导出结果重新纳入快照。
外部路径允许重复导出；项目状态与环境不变时，归档字节保持一致。快照核验、读取与发布遵守
同一项目锁；直接绕过该锁修改文件不在此一致性保证内。

The capsule proves internal integrity and provenance. It does not prove that the scientific model, experiment or conclusion is correct.
