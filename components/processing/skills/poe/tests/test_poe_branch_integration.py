from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: object):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_decode_gbk_and_reject_same_path(tmp_path: Path):
    source = tmp_path / "input.m"
    source.write_bytes("中文模型".encode("gbk"))
    output = tmp_path / "output.txt"
    result = run("decode_matlab_gbk.py", source, output)
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8") == "中文模型"
    assert run("decode_matlab_gbk.py", source, source).returncode != 0


def test_inventory_hashes_files_and_rejects_missing(tmp_path: Path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.txt").write_text("abc", encoding="utf-8")
    result = run("inventory_corpus.py", root, "--out", tmp_path / "inventory")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["files"] == 1
    assert run("inventory_corpus.py", tmp_path / "missing").returncode != 0


def test_case_matrix_rejects_nested_and_oversized(tmp_path: Path):
    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"variables": {"T": [[1], [2]]}}), encoding="utf-8")
    assert run("build_case_matrix.py", nested).returncode != 0
    large = tmp_path / "large.json"
    large.write_text(
        json.dumps({"variables": {"a": list(range(11)), "b": list(range(11))}}),
        encoding="utf-8",
    )
    assert run("build_case_matrix.py", large, "--max-cases", 100).returncode != 0
