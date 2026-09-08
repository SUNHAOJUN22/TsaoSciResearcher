import pytest

from tsao_computation.registries import capabilities, workflows

CAPS = capabilities()
WORKFLOWS = {w["slug"] for w in workflows()}


@pytest.mark.parametrize("record", CAPS, ids=lambda x: x["id"])
def test_capability_record(record):
    assert record["id"].startswith("TSC-")
    assert record["slug"] and record["name_en"] and record["description"]
    assert record["workflow"] in WORKFLOWS
    assert record["inputs"] and record["outputs"] and record["validators"]
    assert record["claim_boundary"]


@pytest.mark.parametrize("record", CAPS, ids=lambda x: x["slug"])
def test_capability_index_file(record):
    from pathlib import Path

    path = Path("capability-index/capabilities") / f"{record['id']}_{record['slug']}.yaml"
    assert path.is_file()
    assert record["slug"] in path.read_text(encoding="utf-8")
