import pytest

from tsao_computation.registries import capabilities, workflows

CAP_IDS = {c["id"] for c in capabilities()}


@pytest.mark.parametrize("record", workflows(), ids=lambda x: x["slug"])
def test_workflow_record(record):
    assert record["keywords"] and record["required_gates"]
    assert record["capability_ids"]
    assert set(record["capability_ids"]) <= CAP_IDS
