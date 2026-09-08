from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    audit_project,
    bootstrap_project,
    deterministic_zip,
    route,
    validate_zip_archive,
)
from .doctor import diagnose
from .provenance import build_manifest
from .snapshot import build_source_snapshot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsao")
    commands = parser.add_subparsers(dest="command", required=True)

    route_parser = commands.add_parser("route", help="classify a process-development brief")
    route_parser.add_argument("text")

    init_parser = commands.add_parser("init", help="initialize a fail-closed project workspace")
    init_parser.add_argument("--brief", required=True)
    init_parser.add_argument("--out", required=True)
    init_parser.add_argument("--templates")

    audit_parser = commands.add_parser("audit", help="audit a TSAO project workspace")
    audit_parser.add_argument(
        "audit_mode",
        nargs="?",
        choices=("initialization", "project", "transition", "release"),
        default="project",
    )
    audit_parser.add_argument("--root", required=True)

    doctor_parser = commands.add_parser("doctor", help="audit repository and provenance integrity")
    doctor_parser.add_argument("--root", default=".")
    doctor_parser.add_argument("--profile", choices=("auto", "core", "full"), default="auto")
    doctor_parser.add_argument(
        "--strict-source-clean",
        action="store_true",
        help="fail when cache or virtual-environment paths are present",
    )
    doctor_parser.add_argument(
        "--refresh-source-manifest",
        action="store_true",
        help="rebuild SOURCE_CORE_MANIFEST.tsv before core verification",
    )

    build_parser = commands.add_parser("build", help="create a deterministic project archive")
    build_parser.add_argument("--root", required=True)
    build_parser.add_argument("--out", required=True)

    snapshot_parser = commands.add_parser(
        "snapshot", help="build a deterministic archive of the public source manifest"
    )
    snapshot_parser.add_argument("--root", default=".")
    snapshot_parser.add_argument("--out", required=True)

    delivery_parser = commands.add_parser(
        "delivery-report", help="emit deterministic software-delivery readiness evidence"
    )
    delivery_parser.add_argument("--root", default=".")
    delivery_parser.add_argument("--strict-source-clean", action="store_true")

    verify_parser = commands.add_parser("verify-archive", help="validate ZIP safety and integrity")
    verify_parser.add_argument("--archive", required=True)

    poe_parser = commands.add_parser("poe", help="POE specialist status, audits and references")
    poe_commands = poe_parser.add_subparsers(dest="poe_command", required=True)
    for name in ("status", "audit-p0", "audit-p1"):
        subcommand = poe_commands.add_parser(name)
        subcommand.add_argument("--root", default=".")
    poe_commands.add_parser("reference-demo")

    package_parser = commands.add_parser(
        "package", help="universal process-package templates and audits"
    )
    package_commands = package_parser.add_subparsers(dest="package_command", required=True)
    package_template = package_commands.add_parser("template")
    package_template.add_argument("--family", required=True)
    package_audit = package_commands.add_parser("audit")
    package_audit.add_argument("--file", required=True)

    epdm_parser = commands.add_parser("epdm", help="EPDM flagship status, audit and references")
    epdm_commands = epdm_parser.add_subparsers(dest="epdm_command", required=True)
    epdm_commands.add_parser("status")
    epdm_audit = epdm_commands.add_parser("audit")
    epdm_audit.add_argument("--file")
    epdm_commands.add_parser("reference-demo")
    epdm_validate = epdm_commands.add_parser(
        "validate-v2", help="validate an EPDM V2 project and its canonical publication"
    )
    epdm_validate.add_argument("--file", required=True)
    epdm_canonicalize = epdm_commands.add_parser(
        "canonicalize", help="publish a deterministic immutable EPDM V2 manifest"
    )
    epdm_canonicalize.add_argument("--file", required=True)
    epdm_canonicalize.add_argument("--out")
    epdm_model = epdm_commands.add_parser(
        "model-suite", help="run the three-level EPDM kinetic and semibatch reference suite"
    )
    epdm_model.add_argument("--temperature-k", type=float, default=323.15)
    epdm_model.add_argument("--residence-s", type=float, default=300.0)
    epdm_acceptance = epdm_commands.add_parser(
        "qualify-acceptance",
        help="run the canonical EPDM software-acceptance qualification",
    )
    epdm_acceptance.add_argument(
        "--project",
        default="skills/epdm/fixtures/v2_phase_a1_reference_project.json",
    )
    epdm_acceptance.add_argument(
        "--output",
        default="reports/runtime/EPDM_SOFTWARE_ACCEPTANCE.json",
    )
    epdm_acceptance.add_argument("--load-samples", type=int, default=5)
    return parser


def _print(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))


def _epdm_model_suite(temperature_K: float, residence_time_s: float) -> dict[str, object]:
    from skills.epdm.core import (
        EpdmActivationEnergies,
        EpdmKineticParameters,
        EpdmKineticState,
        SemibatchFeed,
        SemibatchInventory,
        devolatilization_damkohler,
        entropy_generation_heat_transfer_kW_K,
        flory_huggins_stability_margin,
        semibatch_material_energy_step,
        three_level_kinetic_suite,
    )

    parameters = EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0)
    state = EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1e-6)
    activation = EpdmActivationEnergies(35_000, 37_000, 42_000, 28_000, 45_000, 20_000)
    kinetic_suite = three_level_kinetic_suite(
        state,
        parameters,
        activation,
        temperature_K=temperature_K,
        residence_time_s=residence_time_s,
        site_family_fractions=(0.65, 0.35),
        site_activity_multipliers=(0.75, 1.45),
    )
    semibatch = semibatch_material_energy_step(
        SemibatchInventory(100.0, 120.0, 100.0, 4.0, 0.0, temperature_K, 900.0),
        SemibatchFeed(0.08, 0.06, 0.002, 0.01),
        parameters,
        active_site_mol_L=0.001,
        poison_mol_L=1e-6,
        step_s=min(residence_time_s, 30.0),
        reaction_enthalpy_kJ_mol=85.0,
        heat_removal_kW=7.0,
    )
    return {
        "status": "CALCULATED_REFERENCE_ONLY",
        "model_levels": kinetic_suite,
        "semibatch_reference_step": semibatch,
        "phase_stability_margin": flory_huggins_stability_margin(0.18, 1_500, 0.42),
        "devolatilization_damkohler": devolatilization_damkohler(0.08, 25.0),
        "heat_transfer_entropy_generation_kW_K": entropy_generation_heat_transfer_kW_K(
            80.0, 353.15, 298.15
        ),
        "scientific_technical_approval": "NOT_EVALUATED",
        "engineering_design_approval": "NOT_EVALUATED",
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            root = Path(args.root)
            if args.refresh_source_manifest:
                if args.profile == "full":
                    raise ValueError("full profile cannot refresh only the public-source manifest")
                build_manifest(root, root / "reports/SOURCE_CORE_MANIFEST.tsv")
            result = diagnose(
                root,
                profile=args.profile,
                strict_source_clean=args.strict_source_clean,
            )
            _print(result)
            return 0 if result["pass"] else 2
        if args.command == "route":
            _print(route(args.text))
            return 0
        if args.command == "init":
            templates = Path(args.templates) if args.templates else None
            _print(bootstrap_project(Path(args.brief), Path(args.out), templates))
            return 0
        if args.command == "audit":
            issues = audit_project(Path(args.root), mode=args.audit_mode)
            _print({"pass": not issues, "mode": args.audit_mode, "issues": issues})
            return 0 if not issues else 2
        if args.command == "build":
            _print({"sha256": deterministic_zip(Path(args.root), Path(args.out))})
            return 0
        if args.command == "snapshot":
            _print(build_source_snapshot(Path(args.root), Path(args.out)))
            return 0
        if args.command == "delivery-report":
            from .delivery import delivery_report

            result = delivery_report(
                Path(args.root),
                strict_source_clean=args.strict_source_clean,
            )
            _print(result)
            return 0 if result["pass"] else 2
        if args.command == "verify-archive":
            issues = validate_zip_archive(Path(args.archive))
            _print({"pass": not issues, "issues": issues})
            return 0 if not issues else 2
        if args.command == "package":
            from .process_package import process_package_template, validate_process_package

            if args.package_command == "template":
                _print(process_package_template(args.family))
                return 0
            payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
            result = validate_process_package(payload)
            _print(result)
            return 0 if result["pass"] else 2
        if args.command == "epdm":
            if args.epdm_command == "status":
                import yaml

                manifest = yaml.safe_load(Path("manifest.yaml").read_text(encoding="utf-8"))
                epdm = next(item for item in manifest["subskills"] if item["id"] == "epdm")
                _print({"version": __import__("tsao").__version__, **epdm})
                return 0
            if args.epdm_command == "audit":
                from skills.epdm.package_audit import audit_epdm_process_package

                source = (
                    Path(args.file)
                    if args.file
                    else Path("skills/epdm/fixtures/reference_cases.json")
                )
                payload = json.loads(source.read_text(encoding="utf-8"))
                if not args.file:
                    payload = payload["valid_package"]
                result = audit_epdm_process_package(payload)
                _print(result)
                return 0 if result["pass"] else 2
            if args.epdm_command == "validate-v2":
                from skills.epdm.validation_v2 import validate_v2_project

                payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
                result = validate_v2_project(payload)
                result_payload = result.as_dict()
                _print(result_payload)
                return 0 if result_payload["pass"] else 2
            if args.epdm_command == "canonicalize":
                from skills.epdm.canonical_loader import load_canonical_project_file

                snapshot = load_canonical_project_file(Path(args.file))
                manifest = json.loads(snapshot.to_json())
                if args.out:
                    target = Path(args.out)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                _print(manifest)
                return 0
            if args.epdm_command == "reference-demo":
                from skills.epdm.core import (
                    EpdmKineticParameters,
                    EpdmKineticState,
                    architecture_metrics,
                    heat_removal_margin,
                )

                metrics = architecture_metrics(
                    EpdmKineticState(1.2, 1.0, 0.04, 0.001, 1e-6),
                    EpdmKineticParameters(2.0, 1.6, 0.5, 0.08, 0.02, 10.0),
                    secondary_diene_insertion_probability=0.05,
                    branch_efficiency=0.5,
                    gel_critical_branch_index=1.0,
                )
                _print(
                    {
                        "status": "CALCULATED_REFERENCE_ONLY",
                        "architecture": metrics,
                        "heat_removal_margin": heat_removal_margin(80.0, 110.0),
                        "scientific_technical_approval": "NOT_EVALUATED",
                    }
                )
                return 0
            if args.epdm_command == "model-suite":
                _print(_epdm_model_suite(args.temperature_k, args.residence_s))
                return 0
            if args.epdm_command == "qualify-acceptance":
                from skills.epdm.acceptance import write_acceptance_report

                result = write_acceptance_report(
                    Path(args.output),
                    Path(args.project),
                    load_samples=args.load_samples,
                )
                _print(result.as_dict())
                return 0 if result.pass_ else 2
        if args.command == "poe":
            if args.poe_command == "status":
                import yaml

                root = Path(args.root)
                manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
                poe = next(item for item in manifest["subskills"] if item["id"] == "poe")
                _print({"version": __import__("tsao").__version__, **poe})
                return 0
            if args.poe_command == "audit-p0":
                from skills.poe.scripts.audit_p0 import audit as audit_p0

                result = audit_p0(Path(args.root))
                _print(result)
                return 0 if result["pass"] else 2
            if args.poe_command == "audit-p1":
                from skills.poe.scripts.audit_p1 import audit as audit_p1

                result = audit_p1(Path(args.root))
                _print(result)
                return 0 if result["pass"] else 2
            if args.poe_command == "reference-demo":
                from skills.poe.core import (
                    first_order_cstr_conversion,
                    first_order_pfr_conversion,
                    reactor_reference_suite,
                )

                _print(
                    {
                        "status": "CALCULATED_REFERENCE_ONLY",
                        "reactors": reactor_reference_suite(0.2, 5.0),
                        "PFR": first_order_pfr_conversion(0.2, 5.0),
                        "CSTR": first_order_cstr_conversion(0.2, 5.0),
                        "scientific_technical_approval": "NOT_EVALUATED",
                    }
                )
                return 0
    except (OSError, TypeError, ValueError) as exc:
        print(
            json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
