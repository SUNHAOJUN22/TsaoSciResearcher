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
