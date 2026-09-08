from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .doctor import diagnose
from .skillpacks import skillpack_inventory

_NOT_EVALUATED = "NOT_EVALUATED"
_EXTERNAL_APPROVAL_FIELDS = (
    "scientific_technical_approval",
    "engineering_design_approval",
    "hse_approval",
    "customer_qualification",
    "industrial_performance_guarantee",
)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.as_posix()} must contain a JSON object")
    return payload


def _subskills(root: Path) -> tuple[str, ...]:
    payload = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("subskills"), list):
        raise ValueError("manifest.yaml must contain a subskills list")
    identifiers: list[str] = []
    for item in payload["subskills"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("manifest subskill entries must contain string IDs")
        identifiers.append(item["id"])
    return tuple(sorted(identifiers))


def delivery_report(
    root: Path,
    *,
    strict_source_clean: bool = False,
) -> dict[str, Any]:
    """Return a deterministic software-delivery report without over-claiming approvals."""
    root = Path(root).resolve()
    doctor = diagnose(
        root,
        profile="core",
        strict_source_clean=strict_source_clean,
    )
    skillpacks = skillpack_inventory(str(root))
    release_identity = _read_json_object(root / "reports/RELEASE_IDENTITY.json")
    subskills = _subskills(root)
    readme_assets = tuple(sorted((root / "docs/assets/readme").glob("*.svg")))

    approval_boundary = {
        field: release_identity.get(field, _NOT_EVALUATED) for field in _EXTERNAL_APPROVAL_FIELDS
    }
    approval_boundary_ok = all(value == _NOT_EVALUATED for value in approval_boundary.values())
    release_software_ok = release_identity.get("artifact_software_qualification") == "PASS"
    checks = {
        "doctor": bool(doctor.get("pass")),
        "skillpack_inventory": bool(skillpacks.get("pass")),
        "release_software_identity": release_software_ok,
        "external_approval_boundary": approval_boundary_ok,
        "four_skill_inventory": subskills == ("epdm", "poe", "polymer-general", "process-general"),
        "readme_visual_inventory": len(readme_assets) >= 32,
    }
    passed = all(checks.values())
    return {
        "schema": "TSAO-SOFTWARE-DELIVERY-REPORT-1",
        "version": __version__,
        "pass": passed,
        "software_delivery_readiness": "PASS" if passed else "FAIL",
        "checks": checks,
        "doctor": doctor,
        "skillpack_inventory": skillpacks,
        "inventory": {
            "subskills": list(subskills),
            "readme_svg_assets": len(readme_assets),
            "source_manifest": "reports/SOURCE_CORE_MANIFEST.tsv",
            "source_overlay": "reports/SOURCE_CORE_OVERLAY.tsv",
        },
        "release_identity": {
            "format": release_identity.get("format"),
            "artifact_software_qualification": release_identity.get(
                "artifact_software_qualification"
            ),
            "qualification_boundary": release_identity.get("qualification_boundary"),
        },
        "approval_boundary": approval_boundary,
        "external_holds": [
            field for field, value in approval_boundary.items() if value == _NOT_EVALUATED
        ],
        "statement": (
            "PASS qualifies the repository software artifact only; scientific, engineering, "
            "HSE, customer and industrial approvals remain NOT_EVALUATED."
        ),
    }
