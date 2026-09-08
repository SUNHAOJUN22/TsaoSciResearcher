"""Verify the wire encoding rather than relying on the host console locale."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_worker_wire_is_utf8_under_a_non_utf8_console():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(PYTHONPATH=str(root), PYTHONIOENCODING="cp1252", PYTHONUTF8="0")
    request = {"capability": "research.route", "payload": {"question": "聚合动力学参数与材料研究"}}
    completed = subprocess.run(
        [sys.executable, "-m", "tsao_science.worker"],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env=env, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    response = json.loads(completed.stdout.decode("utf-8"))
    assert response["ok"] is True
    assert "聚合" in completed.stdout.decode("utf-8")


def test_nested_text_attributes_preserve_source_bytes(tmp_path):
    import shutil
    root = Path(__file__).resolve().parents[1]
    component = tmp_path / "components" / "dft"
    component.mkdir(parents=True)
    shutil.copyfile(root / ".gitattributes", tmp_path / ".gitattributes")
    names = (".gitattributes", "LICENSE", "README.md")
    for name in names:
        shutil.copyfile(root / "components" / "dft" / name, component / name)
    expected = {name: (component / name).read_bytes() for name in names}

    def git(*arguments):
        subprocess.run(["git", *arguments], cwd=tmp_path, check=True, capture_output=True, timeout=30)

    git("init")
    git("config", "core.autocrlf", "false")
    git("add", ".")
    git("-c", "user.name=PortabilityTest", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
    git("config", "core.autocrlf", "true")
    for name in names:
        (component / name).unlink()
    git("checkout", "--", "components")
    assert {name: (component / name).read_bytes() for name in names} == expected
