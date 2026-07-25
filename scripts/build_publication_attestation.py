#!/usr/bin/env python3
"""Build an external, non-self-referential attestation for a CI-tested commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts/publication-attestation.json"
SUBJECTS = (
    "artifacts/VALIDATION_EVIDENCE.json",
    "artifacts/QUALITY_HISTORY.json",
    "artifacts/quality-current.json",
    "artifacts/coverage.json",
    "artifacts/mutation-results.json",
    "artifacts/performance.json",
    "artifacts/resolved-environment.lock",
    "artifacts/resolved-environment-sbom.json",
    "docs/SBOM.cdx.json",
    "SHA256SUMS",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_attested_evidence() -> dict[str, Any]:
    path = ROOT / "artifacts/VALIDATION_EVIDENCE.json"
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(value, dict):
        raise ValueError("attested validation evidence root must be an object")
    if value.get("validation_scope") != "current-tree" or value.get("status") != "PASS":
        raise ValueError("publication attestation requires current-tree PASS evidence")
    return value


def build(commit: str, run_id: int, run_attempt: int, job_id: int | None) -> dict[str, Any]:
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("commit must be a lowercase 40-character SHA")
    evidence = _load_attested_evidence()
    provenance = evidence.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("evidence_generated_from_commit") != commit:
        raise ValueError("attested evidence does not match the publication commit")
    subjects = []
    for relative in SUBJECTS:
        path = ROOT / relative
        if path.is_file() and not path.is_symlink():
            subjects.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "1.0",
        "repository": os.environ.get("GITHUB_REPOSITORY", "SUNHAOJUN22/TsaoSciResearcher"),
        "published_commit": commit,
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "workflow_job_id": job_id,
        "subjects": subjects,
        "truth_boundary": "This attestation binds CI artifacts to a commit; it does not grant scientific acceptance.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    parser.add_argument("--run-id", type=int, default=int(os.environ.get("GITHUB_RUN_ID", "0")))
    parser.add_argument("--run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")))
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    if args.run_id < 1 or args.run_attempt < 1:
        raise SystemExit("run id and attempt must be positive")
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    value = build(args.commit, args.run_id, args.run_attempt, args.job_id)
    output.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
