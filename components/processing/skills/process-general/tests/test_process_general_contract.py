from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _require_any(text: str, groups: list[tuple[str, ...]], name: str) -> None:
    missing = [group for group in groups if not any(token in text for token in group)]
    assert missing == [], f"{name}: missing semantic groups {missing}"


def test_manifest_and_module_depth():
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.3.0"
    assert manifest["technical_approval_status"] == "NOT_EVALUATED"
    modules = sorted((ROOT / "modules").glob("*.md"))
    assert len(modules) == 14
    groups = [
        ("decision question", "**decision:**"),
        ("required inputs", "required work", "gate interface"),
        ("executable workflow", "required work", "required professional work"),
        ("failure modes", "fail closed", "hold when"),
        ("exit criteria", "outputs", "required outputs"),
        ("external accountable work", "external-execution", "external accountable"),
    ]
    for path in modules:
        _require_any(path.read_text(encoding="utf-8").casefold(), groups, path.name)


def test_workflow_depth():
    workflows = sorted((ROOT / "workflows").glob("*.md"))
    assert len(workflows) == 6
    for path in workflows:
        text = path.read_text(encoding="utf-8").casefold()
        assert "inputs" in text and "steps" in text and "exit" in text
