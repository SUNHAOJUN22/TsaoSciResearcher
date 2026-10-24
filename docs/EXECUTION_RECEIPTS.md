# External execution receipts

TsaoSciResearcher never launches an external scientific engine through this receipt interface. A receipt records evidence supplied after a real run.

A receipt binds:

- project and guarded handoff identifiers;
- engine name/version and an argument vector, not an opaque shell string;
- timezone-aware start/finish timestamps and duration;
- exit status and evidence level;
- environment metadata;
- regular output files, byte sizes and SHA-256 hashes.

A successful receipt requires exit code zero and at least one checksum-verified output. Verification reloads the registered handoff, checks identity and project ownership, recomputes timestamps and output hashes, and rejects duplicate receipt IDs or output paths.

## Preserve handoff identity

Creating a handoff requires a new output path, except for editing a registered
`draft`/`planned` handoff belonging to the same project with no referencing receipt.
That existing draft-editing behavior is retained. Prepared handoffs, other existing
files and missing registered paths cannot be replaced. A handoff cannot overwrite
its own input. Use a distinct path such as `computation/job-02.json` for a revised
prepared plan. This preserves original input data and the exact handoff referenced
by earlier execution receipts.

The project lock covers the path check, publication and registry update. For new
paths, complete JSON is published using an exclusive hard link from a temporary file in the same
directory, so a concurrent creator cannot be overwritten. A failed registry update
checks the newly created handoff's file identity before rollback. All project
writers must honor the same lock: the identity check and unlink are separate
filesystem operations, not an atomic defense against writers that ignore it.
The operation fails without replacing existing data on filesystems that do not
support hard links; use a supported local filesystem for project state.

### 保留交接文件身份

创建交接文件必须使用新的输出路径；仅保留“当前项目已登记、状态为 `draft`/`planned`、没有回执引用”的草稿编辑能力。已准备好的交接文件、其他已有文件及已登记但丢失的路径均不可覆盖，也不得覆盖当前交接所需的输入。修订已准备好的计划应采用 `computation/job-02.json` 等新路径，从而保留原始输入及历史回执引用的精确交接对象。

路径检查、排他发布和登记更新处于同一项目锁内。对于新路径，完整 JSON 先写入同目录临时文件，再以排他硬链接发布，避免并发创建时覆盖他人文件。登记失败时先检查本次新文件身份再回滚。所有项目写入者必须遵守同一把锁：身份检查与删除是两个文件系统操作，不能对忽略该锁的写入者提供原子保护。不支持硬链接的文件系统会报错并保留既有数据；项目状态应放在支持该功能的本地文件系统。
