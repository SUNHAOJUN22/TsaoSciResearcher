from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tsao_researcher import capsule as capsule_module
from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.errors import LockTimeoutError, ValidationError
from tsao_researcher.handoff import create_handoff
from tsao_researcher.io import exclusive_lock
from tsao_researcher.state import initialize


def _project(tmp_path: Path) -> Path:
    root = initialize("capsule publication", "Does exporting preserve research evidence?", tmp_path)
    (root / "data/input.dat").write_bytes(b"original measured data\n")
    create_handoff(
        root,
        "computation/job.json",
        "Does exporting preserve research evidence?",
        "energy",
        "quantum",
        ["DFT"],
        ["data/input.dat"],
    )
    return root


def _project_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize(
    "relative",
    ["project.yaml", "data/input.dat", "computation/job.json", "exports/new.zip", "data/snapshot.zip"],
)
def test_capsule_cannot_replace_or_create_managed_project_files(tmp_path: Path, relative: str) -> None:
    root = _project(tmp_path)
    (root / "data/snapshot.zip.sha256").write_bytes(b"independent original sidecar data\n")
    before = _project_bytes(root)

    with pytest.raises(ValidationError, match="outside managed project state"):
        export_capsule(root, root / relative, mode="full")

    assert _project_bytes(root) == before
    assert not (root / "exports").exists()


def test_external_capsule_can_be_refreshed_without_changing_project_state(tmp_path: Path) -> None:
    root = _project(tmp_path)
    before = _project_bytes(root)
    archive = tmp_path / "capsule.zip"

    first = export_capsule(root, archive, mode="full")
    first_bytes = archive.read_bytes()
    second = export_capsule(root, archive, mode="full")

    assert archive.read_bytes() == first_bytes
    assert first == second
    assert verify_capsule(archive)["valid"] is True
    assert _project_bytes(root) == before
    with zipfile.ZipFile(archive) as handle:
        manifest = json.loads(handle.read("capsule/manifest.json"))
    reserved_runtime_names = {".mutation.lock", ".tsao-researcher-lock-recovery.guard"}
    expected_paths = {path for path in before if Path(path).name not in reserved_runtime_names}
    assert {row["path"] for row in manifest["files"]} == expected_paths


def test_capsule_rejects_output_parent_linked_into_project(tmp_path: Path) -> None:
    root = _project(tmp_path)
    alias = tmp_path / "linked-data"
    try:
        alias.symlink_to(root / "data", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable")
    before = _project_bytes(root)

    with pytest.raises(ValidationError, match="symbolic-link path component"):
        export_capsule(root, alias / "input.dat", mode="full")

    assert _project_bytes(root) == before


def test_capsule_checks_sidecar_link_before_replacing_external_archive(tmp_path: Path) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    archive.write_bytes(b"existing external archive bytes")
    sidecar = archive.with_name(archive.name + ".sha256")
    try:
        sidecar.symlink_to(root / "data/input.dat")
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links unavailable")
    before = _project_bytes(root)

    with pytest.raises(ValidationError, match="symbolic-link path component"):
        export_capsule(root, archive, mode="full")

    assert archive.read_bytes() == b"existing external archive bytes"
    assert _project_bytes(root) == before


def test_capsule_checks_unusable_sidecar_before_replacing_external_archive(tmp_path: Path) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    archive.write_bytes(b"existing external archive bytes")
    archive.with_name(archive.name + ".sha256").mkdir()
    before = _project_bytes(root)

    with pytest.raises(ValidationError, match="regular file"):
        export_capsule(root, archive, mode="full")

    assert archive.read_bytes() == b"existing external archive bytes"
    assert _project_bytes(root) == before


def test_capsule_holds_project_lock_through_snapshot_reads_and_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    phases: set[str] = set()

    def guarded(owner: Any, name: str) -> None:
        original = getattr(owner, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            with pytest.raises(LockTimeoutError), exclusive_lock(root / "state/.mutation.lock", timeout=0):
                pytest.fail("capsule phase ran without the project mutation lock")
            phases.add(name)
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, name, call)

    for name in ("verify", "verify_receipts", "_project_files", "atomic_write_text"):
        guarded(capsule_module, name)
    guarded(capsule_module.shutil, "copyfileobj")
    guarded(capsule_module.os, "replace")

    result = export_capsule(root, tmp_path / "locked.zip", mode="full")

    assert result["valid"] is True
    assert phases == {
        "verify",
        "verify_receipts",
        "_project_files",
        "atomic_write_text",
        "copyfileobj",
        "replace",
    }
    assert not (root / "state/.mutation.lock").exists()


def test_capsule_read_failure_preserves_existing_archive_and_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    result = export_capsule(root, archive, mode="full")
    sidecar = Path(result["sidecar"])
    before = _project_bytes(root)
    archive_bytes, sidecar_bytes = archive.read_bytes(), sidecar.read_bytes()

    def fail_copy(*args: Any, **kwargs: Any) -> None:
        raise OSError("simulated source read failure")

    monkeypatch.setattr(capsule_module.shutil, "copyfileobj", fail_copy)
    with pytest.raises(OSError, match="simulated source read failure"):
        export_capsule(root, archive, mode="full")

    assert archive.read_bytes() == archive_bytes
    assert sidecar.read_bytes() == sidecar_bytes
    assert _project_bytes(root) == before
    assert not list(tmp_path.glob(".capsule.zip.*"))


def test_backup_failure_preserves_existing_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    result = export_capsule(root, archive, mode="metadata")
    sidecar = Path(result["sidecar"])
    before = archive.read_bytes(), sidecar.read_bytes()

    def fail_link(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected backup failure")

    monkeypatch.setattr(capsule_module.os, "link", fail_link)
    with pytest.raises(OSError, match="injected backup failure"):
        export_capsule(root, archive, mode="full")
    assert (archive.read_bytes(), sidecar.read_bytes()) == before
    assert not list(tmp_path.glob(".capsule.zip.*"))


def test_rollback_failure_retains_old_archive_for_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    result = export_capsule(root, archive, mode="metadata")
    sidecar = Path(result["sidecar"])
    old_zip, old_sidecar = archive.read_bytes(), sidecar.read_bytes()
    replace = capsule_module.os.replace

    def fail_replace(source: Any, target: Any) -> None:
        if Path(target) == sidecar or Path(source).name == "previous.zip":
            raise OSError("injected publish/rollback failure")
        replace(source, target)

    monkeypatch.setattr(capsule_module.os, "replace", fail_replace)
    with pytest.raises(capsule_module.IntegrityError, match="recovery files retained"):
        export_capsule(root, archive, mode="full")
    backups = list(tmp_path.glob(".capsule.zip.publish.*/previous.zip"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == old_zip
    assert sidecar.read_bytes() == old_sidecar


def test_cleanup_failure_reports_warning_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"

    def fail_cleanup(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(capsule_module.shutil, "rmtree", fail_cleanup)
    result = export_capsule(root, archive, mode="full")
    assert result["valid"] is True
    assert verify_capsule(archive)["valid"] is True
    assert Path(result["sidecar"]).read_text().split()[0] == capsule_module.sha256_file(archive)
    assert "capsule cleanup failed; retained" in caplog.text


def test_cleanup_failure_preserves_original_publication_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError("original publication failure")

    def fail_cleanup(*args: Any, **kwargs: Any) -> None:
        raise OSError("secondary cleanup failure")

    monkeypatch.setattr(capsule_module, "atomic_write_text", fail_write)
    monkeypatch.setattr(capsule_module.shutil, "rmtree", fail_cleanup)
    with pytest.raises(OSError, match="original publication failure"):
        export_capsule(root, archive, mode="full")
    assert not archive.exists()
    assert "capsule cleanup failed; retained" in caplog.text


@pytest.mark.parametrize("existing", [False, True])
def test_sidecar_write_failure_preserves_previous_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    sidecar = archive.with_name(archive.name + ".sha256")
    if existing:
        export_capsule(root, archive, mode="metadata")
    before = {p: p.read_bytes() if p.exists() else None for p in (archive, sidecar)}

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected sidecar write failure")

    monkeypatch.setattr(capsule_module, "atomic_write_text", fail_write)
    with pytest.raises(OSError, match="injected sidecar write failure"):
        export_capsule(root, archive, mode="full")
    assert {p: p.read_bytes() if p.exists() else None for p in before} == before


@pytest.mark.parametrize("existing", [False, True])
def test_sidecar_replace_failure_rolls_back_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    root = _project(tmp_path)
    archive = tmp_path / "capsule.zip"
    sidecar = archive.with_name(archive.name + ".sha256")
    if existing:
        export_capsule(root, archive, mode="metadata")
    before = {p: p.read_bytes() if p.exists() else None for p in (archive, sidecar)}
    replace = capsule_module.os.replace

    def fail_sidecar(source: Any, target: Any) -> None:
        if Path(target) == sidecar:
            raise OSError("injected sidecar replace failure")
        replace(source, target)

    monkeypatch.setattr(capsule_module.os, "replace", fail_sidecar)
    with pytest.raises(OSError, match="injected sidecar replace failure"):
        export_capsule(root, archive, mode="full")
    assert {p: p.read_bytes() if p.exists() else None for p in before} == before
    assert not list(tmp_path.glob(".capsule.zip.*"))
