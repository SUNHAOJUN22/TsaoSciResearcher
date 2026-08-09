from __future__ import annotations

from pathlib import Path

from scripts.validate_unicode_integrity import (
    audit_repository,
    normalize_file,
    render_report,
)


def test_clean_unicode_tree_passes_deterministically(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "安全 scientific text\n", encoding="utf-8", newline="\n"
    )

    first = audit_repository(tmp_path)
    second = audit_repository(tmp_path)

    assert first["verdict"] == "PASS"
    assert first["scanned_text_files"] == 1
    assert render_report(first) == render_report(second)


def test_unicode_failures_are_structured(tmp_path: Path) -> None:
    (tmp_path / "bom.md").write_bytes(b"\xef\xbb\xbftext\n")
    (tmp_path / "crlf.txt").write_bytes(b"text\r\n")
    (tmp_path / "missing.py").write_bytes(b"value = 1")
    (tmp_path / "double.json").write_bytes(b"{}\n\n")
    (tmp_path / "replacement.md").write_text(
        f"bad {chr(0xFFFD)} text\n", encoding="utf-8", newline="\n"
    )
    (tmp_path / "nfc.md").write_text(
        f"caf{'e' + chr(0x0301)}\n", encoding="utf-8", newline="\n"
    )
    (tmp_path / "control.txt").write_text(
        f"bad{chr(0)}value\n", encoding="utf-8", newline="\n"
    )
    mojibake = "".join(chr(value) for value in (0x00E4, 0x00B8, 0x00AD))
    (tmp_path / "mojibake.md").write_text(
        f"bad {mojibake} text\n", encoding="utf-8", newline="\n"
    )

    report = audit_repository(tmp_path)

    assert report["verdict"] == "FAIL"
    for key in (
        "replacement_characters",
        "bom_files",
        "line_ending_failures",
        "nfc_failures",
        "control_character_failures",
        "mojibake_failures",
    ):
        assert report[key], key


def test_mechanical_normalization_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "script.py"
    path.write_bytes(b"\xef\xbb\xbfvalue = 'caf\x65\xcc\x81'\r\n\r\n")
    path.chmod(0o754)

    assert normalize_file(path) is True
    assert path.read_text(encoding="utf-8") == "value = 'caf\N{LATIN SMALL LETTER E WITH ACUTE}'\n"
    assert path.stat().st_mode & 0o777 == 0o754
    assert audit_repository(tmp_path)["verdict"] == "PASS"
    assert normalize_file(path) is False
