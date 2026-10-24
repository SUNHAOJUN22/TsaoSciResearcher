"""The tracked text policy must survive a Windows-style Git checkout."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("autocrlf", ["true", "input", "false"])
def test_checkout_preserves_lf_text_and_binary_bytes(tmp_path: Path, autocrlf: str) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    attributes = Path(__file__).resolve().parents[1] / ".gitattributes"
    (repository / ".gitattributes").write_bytes(attributes.read_bytes())
    text = "# 科研结果\nEvidence must remain exact.\n".encode()
    binary = b"%PDF-1.4\r\n\x00\xff\x01\r\n"
    (repository / "README.md").write_bytes(text)
    (repository / "report.pdf").write_bytes(binary)

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(repository), *args], check=True, capture_output=True)

    git("init", "-q")
    git("config", "core.autocrlf", "false")
    git("add", ".gitattributes", "README.md", "report.pdf")
    git("config", "core.autocrlf", autocrlf)
    target = tmp_path / "checkout"
    target.mkdir()
    git("checkout-index", "--all", f"--prefix={target.as_posix()}/")
    assert (target / "README.md").read_bytes() == text
    assert (target / "report.pdf").read_bytes() == binary
