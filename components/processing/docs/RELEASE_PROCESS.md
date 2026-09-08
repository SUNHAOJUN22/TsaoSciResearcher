# Release process

1. Freeze the candidate core and compute its identity.
2. Run two full CI rounds and require identical core hashes.
3. Run two autonomous quick checks under an exclusive lock.
4. Remove caches, bytecode, logs, secrets and unrelated artifacts.
5. Generate file manifest, SBOM and per-file checksums.
6. Build twice with fixed ordering, timestamps and permissions; require byte-for-byte equality.
7. Validate archive CRC, path safety, symlinks, case collisions and checksums.
8. Extract into a random clean directory and re-run CI.
9. Publish external SHA-256, qualification report and exact approval boundary.
10. Any core change after qualification invalidates the release and restarts the process.
