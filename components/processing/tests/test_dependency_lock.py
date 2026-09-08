from __future__ import annotations

from pathlib import Path

from scripts.verify_dependency_lock import verify_lock


def _pyproject(tmp_path: Path) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """
[project]
name = "demo"
version = "0.0.0"
dependencies = ["PyYAML>=6,<7", "jsonschema[format]>=4,<5"]

[project.optional-dependencies]
dev = ["pytest>=8,<10"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


def _hash(char: str) -> str:
    return char * 64


def test_hashed_exact_lock_passes(tmp_path: Path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "\n".join(
            [
                "--index-url https://pypi.org/simple",
                f"jsonschema==4.26.0 --hash=sha256:{_hash('a')}",
                f"pytest==9.0.2 --hash=sha256:{_hash('b')}",
                f"pyyaml==6.0.3 --hash=sha256:{_hash('c')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = verify_lock(lock, _pyproject(tmp_path))
    assert report["status"] == "PASS", report["errors"]
    assert report["package_count"] == 3


def test_lock_rejects_missing_hash_and_direct_dependency(tmp_path: Path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        f"pyyaml==6.0.3 --hash=sha256:{_hash('d')}\npytest==9.0.2\n",
        encoding="utf-8",
    )
    report = verify_lock(lock, _pyproject(tmp_path))
    assert report["status"] == "FAIL"
    assert any("has no SHA-256 hash" in error for error in report["errors"])
    assert "jsonschema" in report["missing_direct_dependencies"]


def test_lock_rejects_credentials_and_non_pinned_rows(tmp_path: Path) -> None:
    lock = tmp_path / "requirements.lock"
    lock.write_text(
        "--index-url https://user:secret@example.com/simple\n"
        "pyyaml>=6\n"
        f"jsonschema==4.26.0 --hash=sha256:{_hash('e')}\n"
        f"pytest==9.0.2 --hash=sha256:{_hash('f')}\n",
        encoding="utf-8",
    )
    report = verify_lock(lock, _pyproject(tmp_path))
    assert report["status"] == "FAIL"
    assert any("must not contain credentials" in error for error in report["errors"])
    assert any("not exactly pinned" in error for error in report["errors"])


def test_committed_lock_covers_windows_pytest_dependency() -> None:
    root = Path(__file__).resolve().parents[1]
    report = verify_lock(root / "requirements.lock", root / "pyproject.toml")
    assert report["status"] == "PASS", report["errors"]
    colorama = report["packages"].get("colorama")
    assert colorama == {
        "version": "0.4.6",
        "hashes": [
            "08695f5cb7ed6e0531a20572697297273c47b8cae5a63ffc6d6ed5c201be6e44",
            "4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6",
        ],
    }
