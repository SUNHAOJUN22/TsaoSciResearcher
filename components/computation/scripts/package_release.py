from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import tarfile
import time
import zipfile
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.provenance.manifest import iter_repository_entries


def release_files(root: Path) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for path in iter_repository_entries(root):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise ValueError(f"release tree contains symlink: {relative.as_posix()}")
        if path.is_file():
            files.append(path)
    return files


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_zip(root: Path, files: list[Path], output: Path, version: str, epoch: int) -> None:
    prefix = f"TsaoSciComputation-{version}"
    timestamp = time.gmtime(max(epoch, 315532800))[:6]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"{prefix}/{relative}", timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build_tar_gz(root: Path, files: list[Path], output: Path, version: str, epoch: int) -> None:
    prefix = f"TsaoSciComputation-{version}"
    with (
        output.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=epoch
        ) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive,
    ):
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = archive.gettarinfo(str(path), arcname=f"{prefix}/{relative}")
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = epoch
            info.mode = 0o644
            with path.open("rb") as handle:
                archive.addfile(info, handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--version", default=Path("VERSION").read_text(encoding="utf-8").strip())
    args = parser.parse_args()
    root = Path(".").resolve()
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1700000000"))
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = release_files(root)
    zip_path = output_dir / f"TsaoSciComputation-{args.version}.zip"
    tar_path = output_dir / f"TsaoSciComputation-{args.version}.tar.gz"
    build_zip(root, files, zip_path, args.version, epoch)
    build_tar_gz(root, files, tar_path, args.version, epoch)
    report = {
        "schema_version": "1.0",
        "version": args.version,
        "source_date_epoch": epoch,
        "file_count": len(files),
        "artifacts": {
            zip_path.name: {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
            tar_path.name: {"bytes": tar_path.stat().st_size, "sha256": sha256(tar_path)},
        },
    }
    report_path = output_dir / "SOURCE_BUILD_REPORT.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    sums = "".join(
        f"{metadata['sha256']}  {name}\n" for name, metadata in sorted(report["artifacts"].items())
    )
    (output_dir / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
