#!/usr/bin/env python3
"""Validate the closed compute-campaign contract and canonical qualification workflow."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "qualify_compute_campaign.py"
CONTRACT_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "benchmark_contract.py"
CAMPAIGN_CONTRACT_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "scripts" / "compute_campaign_contract.py"
CAMPAIGN_SCHEMA_PATH = (
    ROOT / "skills" / "tsao-dft-hpc-provenance" / "templates" / "compute-qualification-campaign.schema.json"
)
CAMPAIGN_PATH = ROOT / "skills" / "tsao-dft-hpc-provenance" / "templates" / "compute-qualification-campaign.yaml"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "tsao_compute_qualification_validation",
        MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _legacy_campaign() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "campaign_id": "LEGACY-CAMPAIGN-CONTRACT-CHECK",
        "benchmark_plan_id": "EXTERNAL-HOLD-BENCHMARK-PLAN",
        "engine": "vasp",
        "reference_candidate_id": "CPU-FP64-REFERENCE",
        "candidate_ids": ["GPU-CANDIDATE"],
        "minimum_repeats": 3,
        "minimum_reference_over_candidate_ratio": 1.05,
        "numerical_tolerances": {
            "energy_ev": {"absolute": 1.0e-6, "relative": 1.0e-8},
        },
    }


def validate() -> dict[str, Any]:
    errors: list[str] = []
    campaign: dict[str, Any] = {}
    hold_report: dict[str, Any] = {}
    campaign_contract: dict[str, Any] = {}
    try:
        module = load_module()
        campaign = module.load_campaign(CAMPAIGN_PATH)
        errors.extend(module.validate_campaign(campaign))
        hold_report = module.qualify(campaign, [])

        if hold_report.get("state") != module.EXTERNAL_HOLD:
            errors.append("repository qualification template must remain EXTERNAL_HOLD")
        if hold_report.get("performance", {}).get("evaluated") is not False:
            errors.append("repository qualification template must not evaluate performance")
        if hold_report.get("workers_bounded_by") != module.MAX_WORKERS:
            errors.append("qualification worker bound is not stable")
        if hold_report.get("campaign_contract") != "canonical-compute-campaign-v1.1":
            errors.append("compute qualification does not declare canonical campaign v1.1")
        if hold_report.get("campaign_schema_version") != "1.1":
            errors.append("compute qualification campaign schema version is not 1.1")
        if hold_report.get("contract_boundary") != ("campaign-policy-independent-from-benchmark-result-evidence"):
            errors.append("campaign and benchmark-result contracts are not explicitly independent")
        if hold_report.get("benchmark_result_contract") != "canonical-nested-v1.1":
            errors.append("compute qualification does not declare the canonical nested v1.1 contract")
        if hold_report.get("input_model") != "canonical-nested-v1.1-typed-accessor":
            errors.append("compute qualification does not use the canonical typed-accessor input model")
        if hold_report.get("normalization_mandatory") is not True:
            errors.append("compute qualification does not declare central normalization mandatory")
        if hold_report.get("native_semantic_validation") is not True:
            errors.append("compute qualification does not declare native semantic validation")
        if hold_report.get("legacy_projection_consumed") is not False:
            errors.append("compute qualification still consumes the legacy flat projection")
        if hold_report.get("legacy_projection_status") != module.PROJECTION_STATUS:
            errors.append("legacy projection status is not explicit and stable")
        if hold_report.get("campaign_document_immutable") is not True:
            errors.append("campaign document immutability is not explicit")
        if module.normalized_workers(10_000, 10_000) != module.MAX_WORKERS:
            errors.append("qualification worker normalization does not enforce the hard bound")

        custom_documents, custom_errors = module.load_results(
            [],
            {"properties": {"schema_version": {"const": "9.9"}}},
        )
        if custom_documents or not any("authoritative nested v1.1" in item for item in custom_errors):
            errors.append("custom schema result input was not rejected from compute qualification")

        bypass = module.qualify(
            campaign,
            [{"schema_version": "9.9", "candidate_id": "unknown"}],
        )
        if bypass.get("performance", {}).get("evaluated") is not False or not bypass.get("errors"):
            errors.append("raw unknown benchmark evidence bypassed central normalization")

        policy = getattr(module, "campaign_policy", None)
        if policy is None:
            errors.append("central compute-campaign contract module is unavailable")
        else:
            campaign_contract = policy.contract_report()
            if campaign_contract.get("ok") is not True:
                errors.append("compute-campaign contract report failed")
            if campaign_contract.get("canonical_contract") != ("canonical-compute-campaign-v1.1"):
                errors.append("campaign contract authority is not canonical v1.1")
            if campaign_contract.get("root_mirror_synchronized") is not True:
                errors.append("root compute-campaign schema mirror is not synchronized")
            if campaign_contract.get("migration_qualification_impact") != ("NO_EVIDENCE_PROMOTION"):
                errors.append("legacy campaign migration impact is not non-promoting")
            if campaign_contract.get("benchmark_result_contract_boundary") != ("independent-canonical-nested-v1.1"):
                errors.append("campaign contract boundary does not name benchmark-result independence")

            canonical_config = module.load_campaign_config(CAMPAIGN_PATH)
            if canonical_config.schema_version != "1.1":
                errors.append("repository campaign template did not load as canonical v1.1")
            try:
                cast(Any, canonical_config.record)["campaign_id"] = "MUTATED"
                errors.append("canonical campaign configuration is mutable")
            except TypeError:
                pass

            legacy_config = policy.prepare_campaign(_legacy_campaign())
            legacy_migration = legacy_config.migration_dict()
            if legacy_config.schema_version != "1.1":
                errors.append("legacy campaign did not migrate to canonical v1.1")
            if legacy_migration.get("source_contract") != ("legacy-compute-campaign-v1.0"):
                errors.append("legacy campaign source contract is not explicit")
            if legacy_migration.get("qualification_impact") != ("NO_EVIDENCE_PROMOTION"):
                errors.append("legacy campaign migration can promote evidence")
            if legacy_migration.get("defaults_applied") != []:
                errors.append("legacy campaign migration applied defaults")
            if legacy_migration.get("evidence_fields_added") != []:
                errors.append("legacy campaign migration fabricated evidence fields")
            legacy_hold = module.qualify(_legacy_campaign(), [])
            if legacy_hold.get("state") != module.EXTERNAL_HOLD:
                errors.append("legacy campaign migration lifted repository EXTERNAL_HOLD")
            if legacy_hold.get("performance", {}).get("evaluated") is not False:
                errors.append("legacy campaign migration enabled performance evaluation")

            mixed = {**_legacy_campaign(), "participants": []}
            unknown = {**_legacy_campaign(), "schema_version": "9.9"}
            for label, invalid in (("mixed", mixed), ("unknown", unknown)):
                report = module.qualify(invalid, [])
                if report.get("state") != module.UNQUALIFIED or not report.get("errors"):
                    errors.append(f"{label} campaign configuration did not fail closed")

        source = MODULE_PATH.read_text(encoding="utf-8")
        contract_source = CONTRACT_PATH.read_text(encoding="utf-8")
        campaign_source = CAMPAIGN_CONTRACT_PATH.read_text(encoding="utf-8")
        campaign_schema_source = CAMPAIGN_SCHEMA_PATH.read_text(encoding="utf-8")
        if "ThreadPoolExecutor" not in source or "executor.map" not in source:
            errors.append("qualification workflow lacks deterministic bounded concurrency")
        if "campaign_policy.prepare_campaign" not in source:
            errors.append("qualification workflow does not use the central campaign adapter")
        if "contract.normalize_record" not in source:
            errors.append("qualification workflow does not use the central benchmark adapter")
        if "performance.validate_canonical_result" not in source:
            errors.append("qualification workflow does not run native canonical semantics")
        if "class CampaignDocument" not in source:
            errors.append("qualification workflow lacks the typed canonical document accessor")
        if "campaign_policy.freeze_tree" not in source:
            errors.append("qualification workflow does not freeze CampaignDocument internals")
        if "contract.compute_qualification_view(" in source:
            errors.append("qualification workflow still calls compute_qualification_view")
        if "def compute_qualification_view" not in contract_source:
            errors.append("legacy diagnostic projection was removed without a compatibility deprecation cycle")
        if "normalized, _ = normalize_record(canonical)" not in contract_source:
            errors.append("legacy diagnostic projection no longer routes through central normalization")
        if '"additionalProperties": false' not in campaign_schema_source or "normalize_campaign" not in campaign_source:
            errors.append("campaign contract is not closed and centrally normalized")
        if len(hold_report.get("identity_invariants") or []) < 7:
            errors.append("compute qualification identity invariants are incomplete")
    except (OSError, RuntimeError, TypeError, ValueError, AttributeError) as exc:
        errors.append(str(exc))

    return {
        "ok": not errors,
        "campaign": campaign.get("campaign_id"),
        "repository_state": hold_report.get("state"),
        "performance_evaluated": hold_report.get("performance", {}).get("evaluated"),
        "campaign_contract": hold_report.get("campaign_contract"),
        "campaign_schema_version": hold_report.get("campaign_schema_version"),
        "campaign_source_contract": hold_report.get("campaign_source_contract"),
        "campaign_migration": hold_report.get("campaign_migration"),
        "campaign_migration_qualification_impact": hold_report.get("campaign_migration_qualification_impact"),
        "campaign_defaults_applied": hold_report.get("campaign_defaults_applied"),
        "campaign_evidence_fields_added": hold_report.get("campaign_evidence_fields_added"),
        "campaign_schema_sha256": campaign_contract.get("canonical_schema_sha256"),
        "campaign_root_mirror_synchronized": campaign_contract.get("root_mirror_synchronized"),
        "campaign_unknown_or_mixed_input": "FAIL_CLOSED",
        "campaign_document_immutable": hold_report.get("campaign_document_immutable"),
        "contract_boundary": hold_report.get("contract_boundary"),
        "benchmark_result_contract": hold_report.get("benchmark_result_contract"),
        "input_model": hold_report.get("input_model"),
        "normalization_mandatory": hold_report.get("normalization_mandatory"),
        "native_semantic_validation": hold_report.get("native_semantic_validation"),
        "legacy_projection_retained": True,
        "legacy_projection_consumed": hold_report.get("legacy_projection_consumed"),
        "legacy_projection_qualification_impact": "NOT_ELIGIBLE",
        "identity_invariants": hold_report.get("identity_invariants"),
        "workers_bounded_by": 8,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    report = validate()
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        print(f"Compute qualification validation: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
