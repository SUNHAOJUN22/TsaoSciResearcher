"""Discovery suggestions cannot authenticate a catalog, project or execution."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import run_python
from tsao_researcher import capabilities, discovery
from tsao_researcher.errors import ValidationError


def _encode(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


@pytest.fixture
def scoped_catalog(tmp_path: Path) -> tuple[Path, Path, Path]:
    row = capabilities.load_capabilities()[0]
    row.update(id="SOURCE-ONE", slug="beforetoken")
    base, extension, index = (tmp_path / name for name in ("base.json", "extension.json", "index.json"))
    base.write_bytes(_encode([row]))
    extension.write_text("[]", encoding="utf-8")
    index.write_bytes(discovery.discovery_index_bytes(base, extension))
    return base, extension, index


@pytest.mark.parametrize(
    ("query", "filters"),
    [
        ("polymer molecular dynamics", {}),
        ("UMAP", {}),
        ("DCCM", {}),
        ("自由能", {}),
        ("citation", {"workflow": "research-integrity"}),
        ("data", {"domains": {"materials", "chemistry"}, "limit": 5}),
        ("  ", {}),
        ("not-an-existing-capability-token", {}),
    ],
)
def test_browse_preserves_ranked_discovery_results_and_declares_limits(
    query: str, filters: dict[str, Any]
) -> None:
    result = discovery.browse_capabilities(query, **filters)
    assert result["results"] == capabilities.search_capabilities(query, **filters)
    assert result["scope"] == "discovery-index-only"
    assert result["source_validation"] == "NOT_PERFORMED"
    assert result["scientific_acceptance"] == "NOT_EVALUATED"
    assert result["authoritative_validation_required"] is True


def test_packaged_index_matches_both_complete_sources() -> None:
    result = discovery.verify_capability_catalog()
    assert result["capability_count"] == 341
    assert result["source_validation"] == "VERIFIED"
    assert result["project_evidence_validation"] == "NOT_PERFORMED"
    assert result["scientific_acceptance"] == "NOT_EVALUATED"
    assert discovery.discovery_index_bytes() == discovery.DISCOVERY_PATH.read_bytes()
    for source in result["sources"]:
        payload = Path(source["path"]).read_bytes()
        assert source["sha256"] == hashlib.sha256(payload).hexdigest()
        assert source["bytes"] == len(payload)


def test_browse_reads_only_index_and_returns_detached_metadata(
    scoped_catalog: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    base, extension, index = scoped_catalog
    base.unlink()
    extension.unlink()
    snapshot = discovery._catalog_snapshot
    reads = []

    def read(path: Path) -> bytes:
        reads.append(path)
        return snapshot(path)

    monkeypatch.setattr(discovery, "_catalog_snapshot", read)
    first = discovery.browse_capabilities("beforetoken", index_path=index)
    assert reads == [index]
    first["declared_sources"][0]["sha256"] = "forged"
    first["results"][0]["domains"].append("injected")
    second = discovery.browse_capabilities("beforetoken", index_path=index)
    assert second["declared_sources"][0]["sha256"] != "forged"
    assert "injected" not in second["results"][0]["domains"]
    assert second["source_validation"] == "NOT_PERFORMED"
    with pytest.raises((OSError, ValidationError)):
        discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)


@pytest.mark.parametrize("atomic", [False, True])
def test_same_stat_source_change_is_not_authenticated_by_old_index(
    scoped_catalog: tuple[Path, Path, Path], atomic: bool
) -> None:
    base, extension, index = scoped_catalog
    verified = discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)
    original = base.stat()
    replacement = base.read_bytes().replace(b"beforetoken", b"after-token")
    destination = base.with_suffix(".replacement") if atomic else base
    destination.write_bytes(replacement)
    os.utime(destination, ns=(original.st_atime_ns, original.st_mtime_ns))
    if atomic:
        destination.replace(base)
    assert base.stat().st_size == original.st_size
    assert base.stat().st_mtime_ns == original.st_mtime_ns
    assert (
        discovery.browse_capabilities("beforetoken", index_path=index)["source_validation"] == "NOT_PERFORMED"
    )
    assert verified["sources"][0]["sha256"] != hashlib.sha256(replacement).hexdigest()
    with pytest.raises(ValidationError, match="does not match"):
        discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)
    index.write_bytes(discovery.discovery_index_bytes(base, extension))
    result = discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)
    assert result["sources"][0]["sha256"] == hashlib.sha256(replacement).hexdigest()


def test_index_same_stat_replacement_cannot_reuse_cached_summaries(
    scoped_catalog: tuple[Path, Path, Path],
) -> None:
    base, extension, index = scoped_catalog
    assert discovery.browse_capabilities("beforetoken", index_path=index)["results"]
    before = index.stat()
    index.write_bytes(index.read_bytes().replace(b"beforetoken", b"after-token"))
    os.utime(index, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert index.stat().st_size == before.st_size
    assert not discovery.browse_capabilities("beforetoken", index_path=index)["results"]
    assert discovery.browse_capabilities("after-token", index_path=index)["results"]
    with pytest.raises(ValidationError, match="does not match"):
        discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)


@pytest.mark.parametrize(
    "broken",
    [b"[", b"\xff", b'[{"id":"x","id":"x","slug":"x"}]', b'[{"id":"x","slug":"x","number":NaN}]'],
)
def test_complete_source_corruption_is_never_hidden_by_successful_prior_verification(
    scoped_catalog: tuple[Path, Path, Path], broken: bytes
) -> None:
    base, extension, index = scoped_catalog
    discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)
    previous = base.stat()
    base.write_bytes(broken.ljust(previous.st_size))
    os.utime(base, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    with pytest.raises((ValueError, ValidationError)):
        discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)


def test_other_scope_requires_full_contract_even_when_weak_loader_was_cached(
    scoped_catalog: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    base, extension, index = scoped_catalog
    other = tmp_path / "other.json"
    other.write_text('[{"id":"SOURCE-ONE","slug":"beforetoken"}]', encoding="utf-8")
    assert capabilities.load_capabilities(other)
    with pytest.raises(ValidationError, match="non-empty string"):
        discovery.verify_capability_catalog(base_path=other, extension_path=extension, index_path=index)
    other.write_bytes(base.read_bytes())
    result = discovery.verify_capability_catalog(base_path=other, extension_path=extension, index_path=index)
    assert result["sources"][0]["path"] == str(other.resolve())
    extension.unlink()
    with pytest.raises((OSError, ValidationError)):
        discovery.verify_capability_catalog(base_path=other, extension_path=extension, index_path=index)


@pytest.mark.parametrize("duplicate_field", ["id", "slug"])
def test_cross_source_duplicates_reject_generation(
    scoped_catalog: tuple[Path, Path, Path], duplicate_field: str
) -> None:
    base, extension, _ = scoped_catalog
    original = json.loads(base.read_bytes())[0]
    row = {**original, "id": "OTHER", "slug": "other"}
    row[duplicate_field] = original[duplicate_field]
    extension.write_bytes(_encode([row]))
    with pytest.raises(ValidationError, match="duplicate"):
        discovery.discovery_index_bytes(base, extension)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("root", "schema", "other"),
        ("root", "purpose", "authoritative"),
        ("root", "claimed_validation", "PASS"),
        ("root", "declared_sources", {}),
        ("root", "declared_sources", []),
        ("root", "capabilities", {}),
        ("source", "name", "../../unrelated.json"),
        ("source", "bytes", True),
        ("source", "bytes", -1),
        ("source", "sha256", 1),
        ("source", "sha256", "z" * 64),
        ("source", "extra", "value"),
        ("row", "name_en", ""),
        ("row", "id", None),
        ("row", "search_text", []),
        ("row", "domains", "domain"),
        ("row", "domains", [1]),
        ("row", "domains", [""]),
        ("row", "source_validation", "VERIFIED"),
    ],
)
def test_malformed_discovery_metadata_cannot_escape_as_authoritative(
    scoped_catalog: tuple[Path, Path, Path], section: str, field: str, value: Any
) -> None:
    _, _, index = scoped_catalog
    data = json.loads(index.read_bytes())
    selected = (
        data if section == "root" else data["declared_sources" if section == "source" else "capabilities"][0]
    )
    selected[field] = value
    index.write_bytes(_encode(data))
    with pytest.raises(ValidationError):
        discovery.browse_capabilities("beforetoken", index_path=index)


@pytest.mark.parametrize("replacement", [[], None, "text"])
def test_non_object_discovery_envelope_rejected(
    scoped_catalog: tuple[Path, Path, Path], replacement: Any
) -> None:
    index = scoped_catalog[2]
    index.write_bytes(_encode(replacement))
    with pytest.raises(ValidationError, match="envelope"):
        discovery.browse_capabilities("x", index_path=index)


@pytest.mark.parametrize("section", ["declared_sources", "capabilities"])
def test_non_object_discovery_members_rejected(scoped_catalog: tuple[Path, Path, Path], section: str) -> None:
    index = scoped_catalog[2]
    data = json.loads(index.read_bytes())
    data[section][0] = None
    index.write_bytes(_encode(data))
    with pytest.raises(ValidationError):
        discovery.browse_capabilities("x", index_path=index)


@pytest.mark.parametrize("duplicate", ["id", "slug"])
def test_duplicate_discovery_summary_rejected(
    scoped_catalog: tuple[Path, Path, Path], duplicate: str
) -> None:
    index = scoped_catalog[2]
    data = json.loads(index.read_bytes())
    row = copy.deepcopy(data["capabilities"][0])
    row["id" if duplicate == "slug" else "slug"] = "different"
    data["capabilities"].append(row)
    index.write_bytes(_encode(data))
    with pytest.raises(ValidationError, match="duplicate"):
        discovery.browse_capabilities("beforetoken", index_path=index)


def test_forged_new_source_hash_does_not_certify_old_summary(scoped_catalog: tuple[Path, Path, Path]) -> None:
    base, extension, index = scoped_catalog
    data = json.loads(index.read_bytes())
    base.write_bytes(base.read_bytes().replace(b"beforetoken", b"after-token"))
    data["declared_sources"][0]["sha256"] = hashlib.sha256(base.read_bytes()).hexdigest()
    index.write_bytes(_encode(data))
    with pytest.raises(ValidationError, match="does not match"):
        discovery.verify_capability_catalog(base_path=base, extension_path=extension, index_path=index)


def test_new_cli_commands_are_dependency_light_and_keep_scopes_explicit() -> None:
    result = run_python(
        [
            "-c",
            """
import builtins, contextlib, io, json, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    assert name.split('.', 1)[0] not in {'yaml', 'jsonschema'}, name
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from tsao_researcher.__main__ import main
for argv, expected in ((['browse', 'polymer', '--limit', '2'], 'NOT_PERFORMED'),
                       (['catalog', 'verify'], 'VERIFIED')):
    sys.argv = ['tsao-researcher', *argv]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main()
    value = json.loads(output.getvalue())
    assert value['source_validation'] == expected
    assert value['scientific_acceptance'] == 'NOT_EVALUATED'
""",
        ]
    )
    assert result.returncode == 0, result.stderr


def test_sync_rebuilds_projection_and_rejects_stale_index(
    scoped_catalog: tuple[Path, Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import sync_runtime_data

    base, extension, _ = scoped_catalog
    root = tmp_path / "repo"
    canonical = root / "capabilities/v2"
    canonical.mkdir(parents=True)
    (canonical / "capabilities.json").write_bytes(base.read_bytes())
    (canonical / "extensions.json").write_bytes(extension.read_bytes())
    monkeypatch.setattr(sync_runtime_data, "ROOT", root)
    monkeypatch.setattr(sync_runtime_data, "MAPPINGS", {})
    monkeypatch.setattr(sys, "argv", ["sync_runtime_data", "--check"])
    with pytest.raises(SystemExit, match="stale"):
        sync_runtime_data.main()
    monkeypatch.setattr(sys, "argv", ["sync_runtime_data", "--write"])
    sync_runtime_data.main()
    monkeypatch.setattr(sys, "argv", ["sync_runtime_data", "--check"])
    sync_runtime_data.main()
    (canonical / "capabilities.json").write_bytes(base.read_bytes().replace(b"beforetoken", b"after-token"))
    with pytest.raises(SystemExit, match="stale"):
        sync_runtime_data.main()
