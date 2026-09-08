from __future__ import annotations

import json
import os
import stat
import zipfile
from datetime import date
from pathlib import Path

import pytest

from tsao.cli import main as cli_main
from tsao.core import (
    ApprovalStatus,
    AssuranceGraph,
    EvidenceItem,
    GateRecord,
    GateStatus,
    ModelRecord,
    audit_project,
    balance_residual,
    bootstrap_project,
    closure_fraction,
    deterministic_zip,
    route,
    stoichiometric_rank,
    validate_gate_sequence,
    validate_zip_archive,
)


def approved_gate(gate_id: str) -> GateRecord:
    return GateRecord(
        gate_id,
        status=GateStatus.PASS,
        owner="owner",
        evidence_ids=[f"EV-{gate_id}"],
        approval_status=ApprovalStatus.APPROVED,
        approver="approver",
    )


def test_router_selects_epdm_and_master_polymer() -> None:
    selected = dict(route("metallocene EPDM with ENB solution polymerization"))
    assert selected["epdm"] > 0
    assert selected["polymer-general"] > 0


def test_router_selects_poe() -> None:
    assert route("POE ethylene octene solution polymerization")[0][0] == "poe"


def test_router_does_not_match_latin_substrings() -> None:
    assert dict(route("poetry analysis")).get("poe") is None


def test_router_falls_back_and_rejects_non_string() -> None:
    assert route("unclassified topic") == [("generic-process", 0.0)]
    with pytest.raises(TypeError):
        route(None)  # type: ignore[arg-type]


def test_gate_pass_is_fail_closed() -> None:
    gate = GateRecord("G3", status=GateStatus.PASS)
    assert set(gate.validate()) == {
        "PASS requires owner",
        "PASS requires evidence",
        "PASS requires approval",
        "PASS requires named approver",
    }


def test_gate_id_must_be_canonical() -> None:
    assert "invalid gate id" in GateRecord("G01").validate()
    assert "invalid gate id" in GateRecord("G19").validate()


def test_gate_transition_to_invalid_pass_rolls_back() -> None:
    gate = GateRecord("G0")
    with pytest.raises(ValueError, match="invalid target Gate state"):
        gate.transition(GateStatus.PASS)
    assert gate.status == GateStatus.NOT_EVALUATED


def test_gate_pass_with_evidence_and_approval() -> None:
    assert approved_gate("G0").validate() == []


def test_illegal_gate_transition_rejected() -> None:
    gate = GateRecord(
        "G0",
        status=GateStatus.RETIRED,
        owner="owner",
        approval_status=ApprovalStatus.APPROVED,
        approver="approver",
    )
    with pytest.raises(ValueError):
        gate.transition(GateStatus.PASS)


def test_gate_sequence_blocks_skipping() -> None:
    gates = [GateRecord(f"G{i}") for i in range(19)]
    gates[2] = approved_gate("G2")
    issues = validate_gate_sequence(gates)
    assert any("G2 cannot PASS before G0, G1" in issue for issue in issues)


def test_gate_sequence_rejects_duplicates() -> None:
    gates = [GateRecord(f"G{i}") for i in range(19)] + [GateRecord("G0")]
    issues = validate_gate_sequence(gates)
    assert "duplicate gate ids: G0" in issues


def test_evidence_rejects_expired_or_open_contradiction() -> None:
    expired = EvidenceItem("EV-1", "A", True, "matching chemistry", "2020-01-01")
    contradicted = EvidenceItem("EV-2", "A", True, "matching chemistry", "2030-01-01", "OPEN")
    assert not expired.usable(date(2026, 7, 21))
    assert not contradicted.usable(date(2026, 7, 21))


def test_evidence_invalid_date_or_state_fails_closed() -> None:
    assert not EvidenceItem("EV", "A", True, "scope", "bad-date").usable()
    assert not EvidenceItem("EV", "A", True, "scope", None, "UNKNOWN").usable()
    assert not EvidenceItem("EV", "A", True, "scope", None, "SUPERSEDED").usable()
    assert EvidenceItem("EV", "A", True, "scope", None, "RESOLVED").usable()


def test_high_risk_model_requires_independent_review() -> None:
    model = ModelRecord("M-1", "MR5", "QUALIFIED", "PASS")
    assert not model.qualified()
    model.independent_reviewer = "independent reviewer"
    assert model.qualified()


def test_invalid_model_enumerations_fail_closed() -> None:
    assert not ModelRecord("M", "MR99", "QUALIFIED", "PASS").qualified()
    assert not ModelRecord("M", "MR1", "MAGIC", "PASS").qualified()
    assert not ModelRecord("M", "MR1", "QUALIFIED", "UNKNOWN").qualified()


def test_mass_balance_and_closure() -> None:
    assert balance_residual({"A": 10}, {"A": 9.8})["A"] == pytest.approx(0.2)
    assert closure_fraction({"A": 10}, {"A": 9.8}) == pytest.approx(0.98)


@pytest.mark.parametrize(
    "values",
    [
        {"A": -1},
        {"A": float("nan")},
        {"A": float("inf")},
    ],
)
def test_flow_validation_rejects_invalid_values(values: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        closure_fraction(values, {"A": 1})


def test_generation_allows_signed_terms() -> None:
    assert balance_residual({"A": 10}, {"A": 8}, {"A": -2})["A"] == pytest.approx(0)


def test_stoichiometric_rank() -> None:
    assert stoichiometric_rank([[1, -1, 0], [0, 1, -1]]) == 2


def test_stoichiometric_rank_rejects_bad_matrices() -> None:
    with pytest.raises(ValueError):
        stoichiometric_rank([])
    with pytest.raises(ValueError):
        stoichiometric_rank([[1, 2], [3]])
    with pytest.raises(ValueError):
        stoichiometric_rank([[1, float("nan")]])


def test_assurance_graph_path_and_orphans() -> None:
    graph = AssuranceGraph()
    graph.add_node("R1", "requirement")
    graph.add_node("E1", "evidence")
    graph.add_node("G1", "gate")
    graph.add_edge("R1", "E1", "supported_by")
    graph.add_edge("E1", "G1", "supports")
    assert graph.has_path("R1", "G1")
    assert graph.orphans() == []


def test_assurance_graph_rejects_invalid_and_duplicate_edges() -> None:
    graph = AssuranceGraph()
    graph.add_node("A", "claim")
    graph.add_node("B", "evidence")
    graph.add_edge("A", "B", "supported_by")
    with pytest.raises(ValueError, match="duplicate edge"):
        graph.add_edge("A", "B", "supported_by")
    assert not graph.has_path("missing", "B")
    with pytest.raises(ValueError):
        graph.add_node("", "claim")


def _write_brief(path: Path, content: str | None = None) -> None:
    path.write_text(
        content or "project_id: DEMO\ntitle: EPDM pilot\nsummary: metallocene EPDM ENB\n",
        encoding="utf-8",
    )


def test_project_bootstrap_and_audit(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    _write_brief(brief)
    root = tmp_path / "project"
    manifest = bootstrap_project(brief, root)
    assert "epdm" in manifest["subskills"]
    assert manifest["technical_approval_status"] == "NOT_EVALUATED"
    assert audit_project(root) == []


def test_bootstrap_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    _write_brief(brief, "- item\n- item2\n")
    with pytest.raises(ValueError, match="YAML mapping"):
        bootstrap_project(brief, tmp_path / "project")


def test_bootstrap_rejects_output_file(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    _write_brief(brief)
    output = tmp_path / "project"
    output.write_text("occupied")
    with pytest.raises(FileExistsError):
        bootstrap_project(brief, output)


def test_bootstrap_rejects_template_symlink(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks unavailable")
    brief = tmp_path / "brief.yaml"
    _write_brief(brief)
    templates = tmp_path / "templates"
    templates.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    try:
        (templates / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not permitted")
    with pytest.raises(ValueError, match="symlink"):
        bootstrap_project(brief, tmp_path / "project", templates)


def test_project_audit_rejects_false_approval_and_bad_gate(tmp_path: Path) -> None:
    brief = tmp_path / "brief.yaml"
    _write_brief(brief, "project_id: DEMO\ntitle: Generic process\n")
    root = tmp_path / "project"
    bootstrap_project(brief, root)
    manifest_path = root / "project_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["technical_approval_status"] = "APPROVED"
    manifest["gates"][1]["status"] = "PASS"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    issues = audit_project(root)
    assert "project must not claim technical approval" in issues
    assert any("G1 cannot PASS before G0" in issue for issue in issues)
    assert any("PASS requires owner" in issue for issue in issues)


def test_deterministic_archive_preserves_empty_directories(tmp_path: Path) -> None:
    root = tmp_path / "source"
    (root / "empty").mkdir(parents=True)
    (root / "a.txt").write_text("alpha")
    first = tmp_path / "one.zip"
    second = tmp_path / "two.zip"
    assert deterministic_zip(root, first) == deterministic_zip(root, second)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert "source/empty/" in archive.namelist()
    assert validate_zip_archive(first) == []


def test_archive_rejects_output_inside_source(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    with pytest.raises(ValueError, match="outside"):
        deterministic_zip(root, root / "archive.zip")


def test_archive_rejects_symlink_and_secret_file(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / ".env").write_text("TOKEN=x")
    with pytest.raises(ValueError, match="secret-like"):
        deterministic_zip(root, tmp_path / "archive.zip")
    (root / ".env").unlink()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    try:
        (root / "link.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not permitted")
    with pytest.raises(ValueError, match="symlink"):
        deterministic_zip(root, tmp_path / "archive.zip")


def test_archive_validator_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")
    assert any("unsafe archive path" in issue for issue in validate_zip_archive(archive_path))


def test_archive_validator_rejects_symlink_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "bad-link.zip"
    info = zipfile.ZipInfo("root/link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(info, "target")
    assert any("symlink" in issue for issue in validate_zip_archive(archive_path))


def test_cli_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    brief = tmp_path / "brief.yaml"
    _write_brief(brief)
    project = tmp_path / "project"
    assert cli_main(["init", "--brief", str(brief), "--out", str(project)]) == 0
    assert cli_main(["audit", "--root", str(project)]) == 0
    archive = tmp_path / "project.zip"
    assert cli_main(["build", "--root", str(project), "--out", str(archive)]) == 0
    assert cli_main(["verify-archive", "--archive", str(archive)]) == 0
    assert '"pass": true' in capsys.readouterr().out


def test_cli_returns_structured_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli_main(["audit", "--root", str(tmp_path / "missing")])
    assert code == 2
    assert '"pass": false' in capsys.readouterr().out
