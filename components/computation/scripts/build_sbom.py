from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/SUNHAOJUN22/TsaoSciComputation"
SELF_OUTPUT_SUFFIXES = (".spdx.json", ".cdx.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_records(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name.endswith(SELF_OUTPUT_SUFFIXES):
            continue
        if path.name in {"RELEASE_MANIFEST.json", "SHA256SUMS"}:
            continue
        records.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
    if match is None:
        raise ValueError(f"cannot parse requirement: {requirement}")
    return match.group(1)


def load_project(root: Path) -> dict[str, Any]:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def created_time(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def build_documents(
    root: Path = ROOT, output_dir: Path | None = None, epoch: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    output = (output_dir or root / "dist").resolve()
    project = load_project(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    artifacts = artifact_records(output)
    resolved_epoch = (
        epoch if epoch is not None else int(os.environ.get("SOURCE_DATE_EPOCH", "1700000000"))
    )
    created = created_time(resolved_epoch)
    fingerprint = hashlib.sha256(
        json.dumps({"version": version, "artifacts": artifacts}, sort_keys=True).encode()
    ).hexdigest()
    namespace = f"{REPOSITORY}/sbom/{version}/{fingerprint}"
    root_ref = f"pkg:pypi/tsao-scicomputation@{version}"

    dependencies: list[dict[str, str]] = []
    runtime_refs: list[str] = []
    for requirement in project.get("dependencies", []):
        name = requirement_name(requirement)
        ref = f"pkg:pypi/{name.lower().replace('_', '-')}"
        runtime_refs.append(ref)
        dependencies.append(
            {"name": name, "requirement": requirement, "group": "runtime", "ref": ref}
        )
    for group, requirements in sorted(project.get("optional-dependencies", {}).items()):
        for requirement in requirements:
            name = requirement_name(requirement)
            ref = f"pkg:pypi/{name.lower().replace('_', '-')}?group={group}"
            dependencies.append(
                {"name": name, "requirement": requirement, "group": group, "ref": ref}
            )

    cyclone_components: list[dict[str, Any]] = [
        {
            "type": "file",
            "name": item["name"],
            "bom-ref": f"artifact:{item['name']}",
            "hashes": [{"alg": "SHA-256", "content": item["sha256"]}],
            "properties": [{"name": "tsao:bytes", "value": str(item["bytes"])}],
        }
        for item in artifacts
    ]
    for item in dependencies:
        cyclone_components.append(
            {
                "type": "library",
                "name": item["name"],
                "bom-ref": item["ref"],
                "purl": item["ref"].split("?", 1)[0],
                "scope": "required" if item["group"] == "runtime" else "optional",
                "properties": [
                    {"name": "tsao:requirement", "value": item["requirement"]},
                    {"name": "tsao:dependency-group", "value": item["group"]},
                ],
            }
        )

    cyclonedx = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, namespace)}",
        "version": 1,
        "metadata": {
            "timestamp": created,
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "TsaoSciComputation SBOM builder",
                        "version": "1.0",
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": "tsao-scicomputation",
                "version": version,
                "bom-ref": root_ref,
                "purl": root_ref,
                "licenses": [{"license": {"id": "MIT"}}],
                "externalReferences": [{"type": "vcs", "url": REPOSITORY}],
            },
        },
        "components": cyclone_components,
        "dependencies": [{"ref": root_ref, "dependsOn": runtime_refs}],
    }

    spdx_packages: list[dict[str, Any]] = [
        {
            "SPDXID": "SPDXRef-Package-TsaoSciComputation",
            "name": "tsao-scicomputation",
            "versionInfo": version,
            "downloadLocation": REPOSITORY,
            "filesAnalyzed": False,
            "licenseConcluded": "MIT",
            "licenseDeclared": "MIT",
            "copyrightText": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": root_ref,
                }
            ],
        }
    ]
    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": "SPDXRef-Package-TsaoSciComputation",
        }
    ]
    for index, item in enumerate(dependencies, start=1):
        spdx_id = f"SPDXRef-Dependency-{index}"
        spdx_packages.append(
            {
                "SPDXID": spdx_id,
                "name": item["name"],
                "versionInfo": item["requirement"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "comment": f"Declared dependency group: {item['group']}",
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-Package-TsaoSciComputation",
                "relationshipType": "DEPENDS_ON" if item["group"] == "runtime" else "OTHER",
                "relatedSpdxElement": spdx_id,
                "comment": "Runtime dependency"
                if item["group"] == "runtime"
                else f"Optional dependency group: {item['group']}",
            }
        )

    spdx_files: list[dict[str, Any]] = []
    for index, item in enumerate(artifacts, start=1):
        spdx_id = f"SPDXRef-Artifact-{index}"
        spdx_files.append(
            {
                "SPDXID": spdx_id,
                "fileName": item["name"],
                "checksums": [{"algorithm": "SHA256", "checksumValue": item["sha256"]}],
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-Package-TsaoSciComputation",
                "relationshipType": "GENERATES",
                "relatedSpdxElement": spdx_id,
            }
        )

    spdx = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"TsaoSciComputation-{version}",
        "documentNamespace": namespace,
        "creationInfo": {
            "created": created,
            "creators": ["Tool: TsaoSciComputation-SBOM-builder-1.0"],
        },
        "packages": spdx_packages,
        "files": spdx_files,
        "relationships": relationships,
    }
    return spdx, cyclonedx


def write_documents(
    root: Path = ROOT, output_dir: Path | None = None, epoch: int | None = None
) -> tuple[Path, Path]:
    output = (output_dir or root / "dist").resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    spdx, cyclonedx = build_documents(root, output, epoch)
    spdx_path = output / f"TsaoSciComputation-{version}.spdx.json"
    cdx_path = output / f"TsaoSciComputation-{version}.cdx.json"
    spdx_path.write_text(
        json.dumps(spdx, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    cdx_path.write_text(
        json.dumps(cyclonedx, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return spdx_path, cdx_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic SPDX and CycloneDX SBOMs.")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    paths = write_documents(ROOT, args.output_dir)
    print(json.dumps({"sboms": [path.name for path in paths]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
