from __future__ import annotations

import hashlib
import json
import os
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from tsao_researcher import capabilities as capabilities_module
from tsao_researcher import capsule as capsule_module
from tsao_researcher import router as router_module
from tsao_researcher import strategy as strategy_module
from tsao_researcher.capabilities import load_capabilities, search_capabilities
from tsao_researcher.capsule import export_capsule, verify_capsule
from tsao_researcher.errors import IntegrityError, ValidationError
from tsao_researcher.handoff import MAX_TEXT_ITEM_CHARS, MAX_TEXT_ITEMS, _clean_string_list
from tsao_researcher.router import load_rules
from tsao_researcher.state import initialize


def _symlink_or_skip(target: Path, link: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


def _valid_capability() -> dict[str, object]:
    return load_capabilities()[0]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda row: row.update(name_en=""), "non-empty string"),
        (lambda row: row.update(domains="bad"), "must be a list"),
        (lambda row: row.update(domains=[""]), "non-empty strings"),
        (lambda row: row.update(source_lineage=["bad"]), "source_lineage"),
        (lambda row: row.update(human_approval={"required": False}), "human_approval"),
        (lambda row: row.update(computation_handoff={"mode": 1}), "computation_handoff"),
    ],
)
def test_strict_capability_contract_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    row = _valid_capability()
    mutate(row)
    path = tmp_path / "capabilities.json"
    path.write_text(json.dumps([row]), encoding="utf-8")
    missing_extension = tmp_path / "missing-extensions.json"
    monkeypatch.setattr(capabilities_module, "CATALOG_PATH", path)
    monkeypatch.setattr(capabilities_module, "EXTENSIONS_PATH", missing_extension)
    capabilities_module._catalog.cache_clear()
    capabilities_module._merged_catalog.cache_clear()
    capabilities_module._single_search_index.cache_clear()
    capabilities_module._merged_search_index.cache_clear()
    with pytest.raises(ValidationError, match=message):
        load_capabilities(path)


def test_capability_search_argument_type_boundaries() -> None:
    with pytest.raises(TypeError, match="workflow"):
        search_capabilities("polymer", workflow=1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="domains"):
        search_capabilities("polymer", domains=["polymer"])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="domains"):
        search_capabilities("polymer", domains={1})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="limit"):
        search_capabilities("polymer", limit=True)


def test_router_rejects_normalized_contradictory_triggers(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(
        json.dumps({"rule": {"positive": ["Alpha"], "negative": ["\uff21\uff2c\uff30\uff28\uff21"]}}),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="contradictory"):
        load_rules(path)
    router_module.clear_rule_cache()


def test_strategy_blank_trigger_short_circuit() -> None:
    strategy_module._compiled_trigger.cache_clear()
    assert strategy_module._contains_trigger("anything", "   ") is False


def test_handoff_linear_cleaner_validation_and_order() -> None:
    assert _clean_string_list(None, field="methods") == []
    with pytest.raises(TypeError, match="list of strings"):
        _clean_string_list("bad", field="methods")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="more than"):
        _clean_string_list(["x"] * (MAX_TEXT_ITEMS + 1), field="methods")
    with pytest.raises(ValidationError, match="exceeds"):
        _clean_string_list(["x" * (MAX_TEXT_ITEM_CHARS + 1)], field="methods")
    assert _clean_string_list([" a ", "", "a", "b"], field="methods") == ["a", "b"]


def test_capsule_rejects_symlink_directories_and_files(tmp_path: Path) -> None:
    project = initialize("capsule", "what is reproducible?", tmp_path / "project")
    target_dir = tmp_path / "outside-directory"
    target_dir.mkdir()
    directory_link = project / "linked-directory"
    _symlink_or_skip(target_dir, directory_link, directory=True)
    with pytest.raises(ValidationError, match="symbolic links"):
        export_capsule(project, tmp_path / "dir-link.zip", mode="full")
    directory_link.unlink()

    target_file = tmp_path / "outside-file"
    target_file.write_text("x", encoding="utf-8")
    file_link = project / "linked-file"
    _symlink_or_skip(target_file, file_link)
    with pytest.raises(ValidationError, match="symbolic links"):
        export_capsule(project, tmp_path / "file-link.zip", mode="full")


def test_capsule_skips_ignored_files_and_nonregular_nodes(tmp_path: Path) -> None:
    project = initialize("capsule", "what is reproducible?", tmp_path / "project")
    (project / ".mutation.lock").write_text("ignored", encoding="utf-8")
    fifo = project / "runtime.fifo"
    if hasattr(os, "mkfifo"):
        os.mkfifo(fifo)
    capsule = tmp_path / "ignored.zip"
    export_capsule(project, capsule, mode="full")
    with zipfile.ZipFile(capsule) as handle:
        names = set(handle.namelist())
    assert "capsule/project/.mutation.lock" not in names
    assert "capsule/project/runtime.fifo" not in names


@pytest.mark.parametrize(
    ("constant", "value", "message"),
    [
        ("MAX_FILE_BYTES", 1, "file exceeds"),
        ("MAX_FILES", 0, "more than"),
        ("MAX_TOTAL_BYTES", 1, "total expanded-size"),
    ],
)
def test_capsule_export_enforces_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    value: int,
    message: str,
) -> None:
    project = initialize("capsule", "what is reproducible?", tmp_path / constant)
    monkeypatch.setattr(capsule_module, constant, value)
    with pytest.raises(ValidationError, match=message):
        export_capsule(project, tmp_path / f"{constant}.zip", mode="full")


def test_capsule_verify_rejects_member_count_directory_and_special_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    too_many = tmp_path / "too-many.zip"
    with zipfile.ZipFile(too_many, "w") as handle:
        handle.writestr("capsule/manifest.json", "{}")
        handle.writestr("capsule/project/a", "a")
    monkeypatch.setattr(capsule_module, "MAX_FILES", 0)
    with pytest.raises(IntegrityError, match="more than"):
        verify_capsule(too_many)
    monkeypatch.setattr(capsule_module, "MAX_FILES", 20_000)

    directory = tmp_path / "directory.zip"
    with zipfile.ZipFile(directory, "w") as handle:
        handle.writestr("capsule/project/folder/", b"")
        handle.writestr("capsule/manifest.json", "{}")
    with pytest.raises(IntegrityError, match="directory"):
        verify_capsule(directory)

    special = tmp_path / "special.zip"
    info = zipfile.ZipInfo("capsule/project/device")
    info.create_system = 3
    info.external_attr = (0o020666 & 0xFFFF) << 16
    with zipfile.ZipFile(special, "w") as handle:
        handle.writestr(info, b"x")
        handle.writestr("capsule/manifest.json", "{}")
    with pytest.raises(IntegrityError, match="non-regular"):
        verify_capsule(special)


def test_capsule_verify_rejects_missing_manifest_duplicate_path_and_checksum(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.zip"
    with zipfile.ZipFile(missing, "w") as handle:
        handle.writestr("capsule/project/a", b"a")
    with pytest.raises(IntegrityError, match="manifest is missing"):
        verify_capsule(missing)

    duplicate = tmp_path / "duplicate-path.zip"
    record = {
        "path": "a",
        "size_bytes": 1,
        "sha256": hashlib.sha256(b"a").hexdigest(),
        "role": "artifact",
    }
    manifest = {"schema_version": "1.0", "files": [record, record], "file_count": 2}
    with zipfile.ZipFile(duplicate, "w") as handle:
        handle.writestr("capsule/manifest.json", json.dumps(manifest))
        handle.writestr("capsule/project/a", b"a")
    with pytest.raises(IntegrityError, match="duplicate or blank"):
        verify_capsule(duplicate)

    mismatch = tmp_path / "checksum.zip"
    record = {"path": "a", "size_bytes": 1, "sha256": "0" * 64, "role": "artifact"}
    manifest = {"schema_version": "1.0", "files": [record], "file_count": 1}
    with zipfile.ZipFile(mismatch, "w") as handle:
        handle.writestr("capsule/manifest.json", json.dumps(manifest))
        handle.writestr("capsule/project/a", b"a")
    with pytest.raises(IntegrityError, match="checksum mismatch"):
        verify_capsule(mismatch)


def test_capsule_verify_encrypted_and_total_size_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeInfo:
        external_attr = 0
        file_size = 1

        def __init__(self, filename: str = "capsule/project/a", *, encrypted: bool = False) -> None:
            self.filename = filename
            self.flag_bits = 1 if encrypted else 0

        def is_dir(self) -> bool:
            return False

    class FakeZip:
        def __init__(self, infos: list[FakeInfo]) -> None:
            self._infos = infos

        def __enter__(self) -> FakeZip:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def infolist(self) -> list[FakeInfo]:
            return self._infos

    capsule = tmp_path / "fake.zip"
    capsule.write_bytes(b"not-read")
    monkeypatch.setattr(
        capsule_module.zipfile,
        "ZipFile",
        lambda path: FakeZip([FakeInfo(encrypted=True)]),
    )
    with pytest.raises(IntegrityError, match="encrypted"):
        verify_capsule(capsule)

    monkeypatch.setattr(capsule_module, "MAX_TOTAL_BYTES", 1)
    monkeypatch.setattr(
        capsule_module.zipfile,
        "ZipFile",
        lambda path: FakeZip([FakeInfo("capsule/project/a"), FakeInfo("capsule/project/b")]),
    )
    with pytest.raises(IntegrityError, match="expanded-size"):
        verify_capsule(capsule)


def test_handoff_rejects_evidence_level_inconsistent_with_readiness(tmp_path: Path) -> None:
    from tsao_researcher.handoff import create_handoff

    project = initialize("handoff", "what should be computed?", tmp_path / "handoff")
    with pytest.raises(ValidationError, match="must be 'planned'"):
        create_handoff(
            project,
            "computation/job.json",
            "what should be computed?",
            "energy",
            "DFT",
            ["DFT"],
            [],
            ready=False,
            evidence_level="prepared",
        )


def test_state_and_quality_helper_boundaries(tmp_path: Path) -> None:
    from tsao_researcher import scientific_quality as quality

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked-project"
    _symlink_or_skip(target, link, directory=True)
    with pytest.raises(ValidationError, match="symbolic-link"):
        initialize("study", "what mechanism?", link)

    with pytest.raises(ValidationError, match="non-empty"):
        quality._text(None, "field")
    with pytest.raises(ValidationError, match="must not be empty"):
        quality._strings([], "field")
    with pytest.raises(ValidationError, match="sequence"):
        quality._optional_strings("bad", "field")
    assert quality._score(0, 0) == 100
