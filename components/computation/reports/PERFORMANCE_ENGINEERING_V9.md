# Performance engineering V9

- Baseline commit: `c2c0eca0fd6bf81cc3cbb1ff29489eefbcba58fd`
- Candidate commit: `6e9f88f4d7413e7351ba34298aba78b441bebbac`
- Audit run: `30235135456`
- Status: `PASS`
- `verify_all --profile all`: `12.270 s` to `8.129 s` (`1.51x`)
- Workflow routing: `260.23x`
- 5 MiB parser throughput: `0.98x`
- Peak RSS ratio: `0.77x`
- Mandatory runtime dependencies added: `0`

The measurements are same-host repository orchestration telemetry. They do not claim faster external scientific solvers or production HPC execution.
