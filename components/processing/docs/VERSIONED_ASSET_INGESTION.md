# Versioned specialist-asset ingestion

The complete EPDM v9, SJTU POE and universal-polymer releases are preserved as independently checksummed qualification artifacts outside this initial source-core PR. Their capabilities are represented in the specialist entrypoints and master contracts in this repository.

A future asset-ingestion PR must:

1. verify the source archive and external SHA-256;
2. scan archive paths, symlinks, case collisions, caches and secrets;
3. record source version, license, provenance and modification status;
4. unpack into a dedicated specialist subtree without changing historical evidence;
5. run the inherited tests in an isolated process group with hard timeout and logs;
6. add migration tests against the TSAO master Gate and approval contracts;
7. retain historical technical states as `NOT_EVALUATED` unless new project evidence exists;
8. build twice deterministically and re-run CI from a clean extraction.

This avoids opaque binary blobs in source history and prevents a specialist archive from silently weakening TSAO governance.
