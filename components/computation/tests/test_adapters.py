import pytest

from tsao_computation.registries import adapters, workflows

RECORDS = adapters()
WORKFLOWS = {w["slug"] for w in workflows()}


@pytest.mark.parametrize("record", RECORDS, ids=lambda x: x["slug"])
def test_adapter_record(record):
    assert record["workflow"] in WORKFLOWS
    assert record["maturity"].startswith("A")
    assert record["live_execution_verified"] is False
    assert isinstance(record["executables"], list)
