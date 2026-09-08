from __future__ import annotations

import json
import re
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.provenance.manifest import iter_repository_entries

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".zip", ".whl", ".gz", ".pyc"}
PATTERNS = {
    "private_key": re.compile("-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile("gh[pousr]_[A-Za-z0-9]{30,}"),
    "aws_key": re.compile("AKIA[0-9A-Z]{16}"),
    "dangerous_eval": re.compile(r"\b(?:eval|exec)\s*\("),
    "shell_true": re.compile(r"shell\s*=\s*True"),
}
MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern.pattern})" for name, pattern in PATTERNS.items())
)


def scan(root: Path) -> dict[str, object]:
    root = root.resolve()
    findings: list[dict[str, object]] = []
    scanned = 0
    for path in iter_repository_entries(root):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "scripts/security_scan.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for match in MASTER_PATTERN.finditer(text):
            rule = match.lastgroup
            if rule is None:
                continue
            findings.append({"path": relative, "rule": rule, "offset": match.start()})
    return {"schema_version": "1.0", "files_scanned": scanned, "findings": findings}


def main() -> int:
    report = scan(Path("."))
    output = Path("evidence/security-scan.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, sort_keys=True))
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
