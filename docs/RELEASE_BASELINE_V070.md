# TsaoSciResearcher v0.7.0 Immutable Release Baseline

## Release identity

- Version: `v0.7.0`
- Immutable source commit: `716b0bc30d7ce34b478173b77c56e548a631aee7`
- Annotated tag object: `54a7d500891dd9881c434a28cacdc40b6017729b`
- GitHub Release: `https://github.com/SUNHAOJUN22/TsaoSciResearcher/releases/tag/v0.7.0`
- Published at: `2026-07-31T03:33:21Z`
- Release state: final, not draft, not prerelease

The `v0.7.0` tag is frozen at the immutable source commit above. This document is a post-release record on `main`; it does not and must not move or rewrite the tag.

## Exact validation provenance

- Exact-main attestation run: `30598726544`
- Exact-main attestation artifact: `exact-main-attestation-716b0bc30d7ce34b478173b77c56e548a631aee7`
- Exact-main artifact ID: `8781135259`
- Exact-main artifact SHA-256: `a8790b1df8b990dce94ab9590a0070899814bf3fcc59334ab5ccb83403b0a1be`
- Release acceptance run: `30602264345`

Verified release baseline:

- 240 tests passed; 0 failures, 0 errors, 0 skips;
- line coverage: 95.726%;
- branch coverage: 92.708%;
- mutation: 24/24 killed; 0 survivors;
- Ubuntu Python 3.10 and 3.13, Windows Python 3.12, and macOS Python 3.12 compatibility: PASS;
- Ruff, strict Mypy, Bandit, and exact-lock vulnerability audit: PASS;
- deterministic source ZIP: PASS;
- wheel and sdist isolated installation: PASS.

## Release acceptance

The official GitHub Release assets were downloaded again after publication. Acceptance confirmed:

- the annotated tag targets the immutable source commit;
- the Release is neither draft nor prerelease;
- every asset matches `RELEASE-SHA256SUMS`;
- the source ZIP matches its external SHA-256 sidecar;
- source ZIP members contain no absolute paths, parent traversal, duplicate names, or symbolic links;
- `SHA256SUMS` and `.sha256` files are intentionally external to the source ZIP to avoid self-reference;
- rebuilding the source ZIP from the downloaded source produced a byte-identical archive and sidecar;
- the official wheel and sdist installed in independent clean virtual environments;
- `pip check`, package version, CLI, routing, strategy, and execution-boundary checks passed.

## Asset digests

| Asset | SHA-256 |
|---|---|
| `EXACT-MAIN-ATTESTATION.txt` | `e90fe648306a68603bc326df5337893a22b4d2aac92974341aa9b71eac61f4a1` |
| `INSTALL-VERIFY.md` | `6474e61f858b49b174d1fef748bac5db71554eb3ed26996b39703ad50ca8d25e` |
| `LICENSE` | `15d3bd290421f9d5f3e1ab91f0d5b27ab13cea8583c7d7e5f289a0f04c216fc4` |
| `NOTICE` | `6cd40c810f8fb7a54b60c17a0f7eb7cebcdf7f57e583ffd8d0fcb4c22b0b7472` |
| `QUALITY_HISTORY.json` | `f10911b2aa8d789ab0dd3dc6d95635fbf1401dd6170c210f3b7ad668229a18db` |
| `RELEASE_NOTES.md` | `e5a118ec48b91c128096025865e43104e9a17558235f544c8f2f52d60191dca1` |
| `SBOM.cdx.json` | `72b43f7757ce08d880381a0b27422efa7d0463736cf939c14f98491781685cd1` |
| `SHA256SUMS` | `d6bd4ec18117c956426ab9c0a04572e6d59faf53783b9bf3d20ffb9b7e97676c` |
| `THIRD_PARTY.md` | `ded982d020c172860a0b6f58b604681f2c342fc7148880ea763e7c809d78367a` |
| `TsaoSciResearcher-v0.7.0.zip` | `7bd016c8748412fe0d7b3616dd778142e820e08c7d298315de8447effa6d9428` |
| `TsaoSciResearcher-v0.7.0.zip.sha256` | `2364ef8aeb0e26438c96f2d945f7384b664e3fd105f6756804ab74407c4f6e33` |
| `VALIDATION_EVIDENCE.json` | `a30a28125bd42197cb5155a6fa43ab0dc4fa9d208eb871f1a73a764acac0e7d7` |
| `coverage.json` | `e63b1b081abaf7d8b8016fa840346672e2e5d7ba90433938e8571b48dc6ac606` |
| `coverage.xml` | `88f8da8380d4efc3e8188c2e9309be1935450396c379a193f936a13960a36005` |
| `engineering-audit-report.pdf` | `23883a2e3a505b57f2a5f03040d506c484c3ed7697615555ae9d6183bb5aac2a` |
| `junit.xml` | `2ca16b913d45f514f1714533a1403418f0e74180052df492a0bc0b04994faa5d` |
| `mutation-results.json` | `c726d2157be5969506e3ab79dc0b459b68e9e03ea574513b3e988c8bf513b4ee` |
| `performance.json` | `0331c6521e0ed7bffbcad30fe9b16081e7b26939e3cd2e69bd4c7872551d6301` |
| `publication-attestation.json` | `979f001a2a387d861d51e34b0c408795535092cb97d2d9e8edbc87145de3d0e7` |
| `quality-current.json` | `b5380021dfadd510f5e83986c6c3728b9608403faa55072efaba39af86354fa1` |
| `resolved-environment-sbom.json` | `087e1edf1e498363099df2d063750a58b3e256c9ada73c27a8b0a915ed8b0e54` |
| `resolved-environment.lock` | `1a8bf175e9b266ae613b748adb5c42ef7079f2394bf0a9f6ea6a8032a70139ae` |
| `tsao_sci_researcher-0.7.0-py3-none-any.whl` | `e8879003d26f6c3d1003b954e09b50161dab08fe1dc0c6237a604862c8fa5448` |
| `tsao_sci_researcher-0.7.0.tar.gz` | `ae0d8ab700201bc1549a5a4f4061c9134ec5b72427802b72d451bdf322d9b005` |
| `RELEASE-ASSET-MANIFEST.json` | `724a6cd071ee028bcd5c451c85fcbebdc2ca85bec55da3539b32657ddcedb3fc` |
| `RELEASE-SHA256SUMS` | `82f818849040397a3ad1d9483c2eef46434106028af931b847db47ddd281ae95` |

## Scientific truth boundary

TsaoSciResearcher recommends, routes, records, and validates scientific workflows. A strategy recommendation, computation handoff, execution receipt, or software validation does not mean that an external DFT, quantum-chemistry, MD, FEM, CFD, HPC, instrument, or laboratory run occurred. Receipt of output does not prove convergence or model validity, and software verification does not grant scientific acceptance. High-impact conclusions still require appropriate independent evidence and qualified human approval.

## Freeze policy

- No new capability or behavior may be added under the `0.7.0` version identity.
- The `v0.7.0` tag and published assets must not be moved, replaced, or silently refreshed.
- Any release-blocking correction must use a new patch version and a new immutable tag.
- Subsequent feature development belongs to `0.8.0-dev` or a later explicitly declared version.
