# Software supply-chain controls

The repository uses an exact direct CI toolchain lock, pinned GitHub Action commit SHAs, source security checks, dependency vulnerability auditing, a deterministic direct-dependency CycloneDX 1.6 SBOM, reproducible source ZIPs, wheel/sdist builds and an external publication attestation.

`docs/SBOM.cdx.json` records the direct locked CI inventory and the lock-file digest. `pip-audit` evaluates the resolved installed environment, including transitive packages, and emits a separate environment SBOM artifact plus a sorted resolved-environment lock snapshot. These are complementary controls: the SBOM is an inventory, not a vulnerability assessment.

Release artifacts include checksums, SBOM, validation evidence and an attestation binding CI subjects to the tested commit. Secrets, private manuscripts and proprietary data must never be embedded in a capsule or release asset without explicit authorization.
