import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills/tsao-dft-hpc-provenance/scripts/scientific_acceptance_gate_v6.py"
spec = importlib.util.spec_from_file_location("scientific_acceptance_gate_v6", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_parser_fatal_dominates_all_other_receipts() -> None:
    result = module.evaluate_dft_acceptance(
        parser_receipt={"parser_accepted": False, "fatal": True},
        quantity_receipt={"status": "PASS"},
        kinetics_receipt={"status": "VALID", "standard_state_explicit": True},
        model_receipt={"status": "ACCEPTED", "independent_approval_verified": True},
        external_execution_receipt={"status": "VERIFIED_FOR_BOUND_OUTPUT", "artifact_sha256": "a" * 64},
    )
    assert result.software_integrity_status == "FAIL"
    assert result.scientific_acceptance_status == "HOLD"


def test_software_pass_without_external_engine_stays_external_hold() -> None:
    result = module.evaluate_dft_acceptance(
        parser_receipt={"parser_accepted": True, "fatal": False},
        quantity_receipt={"status": "PASS"},
        kinetics_receipt=None,
        model_receipt=None,
        external_execution_receipt=None,
    )
    assert result.software_integrity_status == "PASS"
    assert result.external_execution_status == "EXTERNAL_DFT_EXECUTION_NOT_VERIFIED"
    assert result.scientific_acceptance_status == "HOLD"


def test_bound_output_only_becomes_ready_for_review_not_accepted() -> None:
    result = module.evaluate_dft_acceptance(
        parser_receipt={"parser_accepted": True, "fatal": False},
        quantity_receipt={"status": "PASS"},
        kinetics_receipt={"status": "VALID", "standard_state_explicit": True},
        model_receipt={"status": "ACCEPTED", "independent_approval_verified": True},
        external_execution_receipt={"status": "VERIFIED_FOR_BOUND_OUTPUT", "artifact_sha256": "a" * 64},
    )
    assert result.scientific_acceptance_status == "READY_FOR_INDEPENDENT_SCIENTIFIC_REVIEW"
    assert "INDEPENDENT_SCIENTIFIC_REVIEW_REQUIRED" in result.reason_codes
