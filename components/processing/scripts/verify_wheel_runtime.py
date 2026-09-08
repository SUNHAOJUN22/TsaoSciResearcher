#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _choose_wheel(wheel_dir: Path) -> Path:
    wheels = sorted(wheel_dir.glob("*.whl")) if wheel_dir.is_dir() else []
    if len(wheels) != 1:
        raise ValueError(f"expected exactly one wheel in {wheel_dir}, found {len(wheels)}")
    return wheels[0]


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _venv_python(venv_root: Path) -> Path:
    return venv_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _runtime_code(extra_sys_path: Path | None = None) -> str:
    path_setup = f"sys.path.insert(0, {str(extra_sys_path)!r})\n" if extra_sys_path else ""
    return f"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote
{path_setup}from importlib.resources import files
import numpy as np
import skills.epdm
import skills.poe
import tsao
from tsao.process_package import validate_process_package
from tsao.skillpacks import skillpack_inventory
from skills.epdm.core import active_site_fraction, heat_removal_margin, validate_epdm_case
from skills.epdm.reaction_network import audit_reaction_network, build_reaction_network
from skills.epdm.executable_rhs import (
    build_calculated_reference_rate_package,
    execute_structural_rhs,
)
from skills.epdm.state_generator import generate_state_definition
from skills.epdm.numerical_integration import build_integration_request, integrate_adaptive
from skills.poe.core import (
    first_order_pfr_conversion,
    fit_first_order_rate,
    fopdt_response,
    validate_model_passport_registry,
)
pfr = first_order_pfr_conversion(0.2, 5.0)
times = np.linspace(0.0, 20.0, 41)
fit = fit_first_order_rate(times, 1.0 - np.exp(-0.2 * times), lower_s=0.01, upper_s=1.0)
response = fopdt_response([0.0, 1.0, 10.0], gain=1.0, time_constant_s=2.0)
passport = json.loads(files('skills.poe').joinpath('data/model_asset_passports.json').read_text(encoding='utf-8'))
validated = validate_model_passport_registry(passport)
epdm = json.loads(files('skills.epdm').joinpath('fixtures/reference_cases.json').read_text(encoding='utf-8'))
case = validate_epdm_case(epdm['valid_case'])
package = validate_process_package(epdm['valid_package'])
a2_state = generate_state_definition(
    source_state_definition_id='EPDM-V2-STATE-REFERENCE',
    model_level=2,
    site_family_ids=('SITE-A',),
)
a2_network = build_reaction_network(a2_state)
a2_audit = audit_reaction_network(a2_network, a2_state)
a3_package = build_calculated_reference_rate_package(a2_network)
a3_input = a2_state.pack({{'N_SITE_POTENTIAL:SITE-A': 1.0}}, fill_missing=0.0)
a3_result = execute_structural_rhs(
    a2_network, a2_state, a3_package, a3_input, temperature_k=323.15, volume_m3=1.0
)
a15_request = build_integration_request(
    a2_network, a2_state, a3_package,
    time_start_s=0.0, time_end_s=0.01, initial_step_s=0.001,
    minimum_step_s=1.0e-8, maximum_step_s=0.005,
)
a15_result = integrate_adaptive(
    a15_request, a2_network, a2_state, a3_package, a2_state.zeros(),
    temperature_k=323.15, volume_m3=1.0,
)
skillpacks = skillpack_inventory()
skillpack_root = Path(skillpacks['root'])
link_pattern = re.compile(r"\\[[^\\]]*\\]\\(([^)]+)\\)")
link_failures = []
for readme_name in ('README.md', 'README.zh-CN.md'):
    readme_path = skillpack_root / readme_name
    for raw_target in link_pattern.findall(readme_path.read_text(encoding='utf-8')):
        link_target = raw_target.strip().strip('<>')
        if not link_target or link_target.startswith(('#', 'http://', 'https://', 'mailto:')):
            continue
        link_target = unquote(link_target.split('#', 1)[0].split('?', 1)[0])
        if not link_target or any(character in link_target for character in '{{}}*|'):
            continue
        resolved = (readme_path.parent / link_target).resolve(strict=False)
        try:
            resolved.relative_to(skillpack_root.resolve())
        except ValueError:
            link_failures.append(f"{{readme_name}} -> escapes root: {{raw_target}}")
            continue
        if not resolved.exists():
            link_failures.append(f"{{readme_name}} -> missing: {{raw_target}}")
print(json.dumps({{
    'tsao_module_path': str(Path(tsao.__file__).resolve()),
    'epdm_module_path': str(Path(skills.epdm.__file__).resolve()),
    'poe_module_path': str(Path(skills.poe.__file__).resolve()),
    'python_prefix': sys.prefix,
    'pfr': pfr,
    'fit': fit['rate_constant_s'],
    'response': response.tolist(),
    'passport_status': validated['status'],
    'active_site': active_site_fraction(10, 6),
    'heat_margin': heat_removal_margin(80, 100),
    'epdm_status': case['status'],
    'package_status': package['status'],
    'a2_state_count': a2_state.size,
    'a2_reaction_count': len(a2_network.channels),
    'a2_propagation_channel_count': a2_audit.metrics['propagation_channel_count'],
    'a2_network_status': a2_audit.decision.value,
    'a2_numerical_execution': a2_network.as_dict()['numerical_execution'],
    'a3_binding_count': len(a3_package.bindings),
    'a3_rhs_decision': a3_result.decision.value,
    'a3_rhs_reason_code': a3_result.reason_code,
    'a3_scientific_status': a3_result.as_dict()['scientific_status'],
    'a3_scientific_technical_approval': a3_result.as_dict()['scientific_technical_approval'],
    'a15_integration_decision': a15_result.decision.value,
    'a15_integration_reason_code': a15_result.reason_code,
    'a15_integration_method': a15_result.request.integration_method.value,
    'a15_time_monotonic': a15_result.conservation.get('time_monotonic'),
    'a15_scientific_status': a15_result.scientific_status,
    'a15_scientific_technical_approval': a15_result.scientific_technical_approval,
    'skillpacks': skillpacks,
    'installed_readme_link_failures': link_failures,
}}))
"""


def _path_is_within(raw_path: object, expected_root: Path) -> bool:
    if not isinstance(raw_path, str) or not raw_path:
        return False
    try:
        Path(raw_path).resolve(strict=False).relative_to(expected_root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _evaluate_payload(
    payload: dict[str, object],
    label: str,
    *,
    expected_root: Path,
) -> list[str]:
    errors: list[str] = []
    if abs(float(payload.get("pfr", 0.0)) - (1.0 - math.exp(-1.0))) > 1e-12:
        errors.append(f"{label} PFR known solution mismatch")
    if abs(float(payload.get("fit", 0.0)) - 0.2) > 1e-5:
        errors.append(f"{label} parameter-fit known solution mismatch")
    if payload.get("epdm_status") != "PASS":
        errors.append(f"{label} EPDM reference validation failed")
    if payload.get("package_status") != "PASS":
        errors.append(f"{label} universal package validation failed")
    if payload.get("a2_state_count") != 20:
        errors.append(f"{label} A2 generated-state size mismatch")
    if payload.get("a2_reaction_count") != 41:
        errors.append(f"{label} A2 reaction-network size mismatch")
    if payload.get("a2_propagation_channel_count") != 9:
        errors.append(f"{label} A2 propagation matrix is incomplete")
    if payload.get("a2_network_status") != "PASS":
        errors.append(f"{label} A2 reaction-network structural audit failed")
    if payload.get("a2_numerical_execution") != "NOT_IMPLEMENTED_PHASE_A2":
        errors.append(f"{label} A2 numerical-execution boundary mismatch")
    if payload.get("a3_binding_count") != 41:
        errors.append(f"{label} A3 rate-package binding count mismatch")
    if payload.get("a3_rhs_decision") != "PASS":
        errors.append(f"{label} A3 executable RHS smoke failed")
    if payload.get("a3_rhs_reason_code") != "A3_RHS_SOFTWARE_VERIFIED":
        errors.append(f"{label} A3 RHS reason-code mismatch")
    if payload.get("a3_scientific_status") != "CALCULATED_REFERENCE_ONLY":
        errors.append(f"{label} A3 scientific-status boundary mismatch")
    if payload.get("a3_scientific_technical_approval") != "NOT_EVALUATED":
        errors.append(f"{label} A3 scientific approval boundary mismatch")
    if payload.get("a15_integration_decision") != "PASS":
        errors.append(f"{label} A15 adaptive integration smoke failed")
    if payload.get("a15_integration_reason_code") != "A15_ADAPTIVE_INTEGRATION_COMPLETE":
        errors.append(f"{label} A15 integration reason-code mismatch")
    if payload.get("a15_integration_method") != "ADAPTIVE_DORMAND_PRINCE_54":
        errors.append(f"{label} A15 integration-method mismatch")
    if payload.get("a15_time_monotonic") is not True:
        errors.append(f"{label} A15 monotonic-time gate failed")
    if payload.get("a15_scientific_status") != "CALCULATED_REFERENCE_ONLY":
        errors.append(f"{label} A15 scientific-status boundary mismatch")
    if payload.get("a15_scientific_technical_approval") != "NOT_EVALUATED":
        errors.append(f"{label} A15 scientific approval boundary mismatch")

    for field in ("tsao_module_path", "epdm_module_path", "poe_module_path"):
        if not _path_is_within(payload.get(field), expected_root):
            errors.append(f"{label} imported {field} outside the installed root")

    skillpacks = payload.get("skillpacks")
    if not isinstance(skillpacks, dict) or not skillpacks.get("pass"):
        errors.append(f"{label} skillpack inventory failed")
    else:
        if skillpacks.get("delivery") != "INSTALLED_SKILLPACK":
            errors.append(f"{label} did not resolve the installed skillpack data root")
        if not _path_is_within(skillpacks.get("root"), expected_root):
            errors.append(f"{label} resolved Skillpack data outside the installed root")
        if skillpacks.get("readme_svg_assets", 0) < 29:
            errors.append(f"{label} does not contain all 29 README assets")
        if skillpacks.get("process_general_modules_present") != 14:
            errors.append(f"{label} process-general module registry is incomplete")
        if skillpacks.get("process_general_workflows_present") != 6:
            errors.append(f"{label} process-general workflow registry is incomplete")

    if payload.get("installed_readme_link_failures"):
        errors.extend(
            f"{label} README link failure: {failure}"
            for failure in payload["installed_readme_link_failures"]
        )
    return errors


def _execute_runtime(
    python_executable: Path,
    *,
    cwd: Path,
    label: str,
    expected_root: Path,
    extra_sys_path: Path | None = None,
) -> tuple[dict[str, object], list[str]]:
    completed = _run(
        [str(python_executable), "-I", "-c", _runtime_code(extra_sys_path)],
        cwd=cwd,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "runtime failed"
        return {}, [f"{label}: {message}"]
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {}, [f"{label} returned invalid JSON: {exc}"]
    return payload, _evaluate_payload(payload, label, expected_root=expected_root)


def _verify_target_install(wheel: Path, directory: Path) -> tuple[dict[str, object], list[str]]:
    target = directory / "target-site"
    install = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-deps",
            "--target",
            str(target),
            str(wheel.resolve()),
        ],
        cwd=directory,
    )
    if install.returncode != 0:
        message = install.stderr.strip() or install.stdout.strip() or "installation failed"
        return {}, [f"PIP_TARGET: {message}"]
    return _execute_runtime(
        Path(sys.executable),
        cwd=directory,
        label="PIP_TARGET",
        expected_root=target,
        extra_sys_path=target,
    )


def _verify_standard_venv(wheel: Path, directory: Path) -> tuple[dict[str, object], list[str]]:
    venv_root = directory / "standard-venv"
    create = _run(
        [sys.executable, "-m", "venv", str(venv_root)],
        cwd=directory,
    )
    if create.returncode != 0:
        message = create.stderr.strip() or create.stdout.strip() or "venv creation failed"
        return {}, [f"STANDARD_VENV: {message}"]
    python_executable = _venv_python(venv_root)
    install = _run(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--quiet",
            str(wheel.resolve()),
        ],
        cwd=directory,
    )
    if install.returncode != 0:
        message = install.stderr.strip() or install.stdout.strip() or "installation failed"
        return {}, [f"STANDARD_VENV: {message}"]
    dependency_check = _run([str(python_executable), "-m", "pip", "check"], cwd=directory)
    if dependency_check.returncode != 0:
        message = dependency_check.stderr.strip() or dependency_check.stdout.strip()
        return {}, [f"STANDARD_VENV dependency check failed: {message}"]
    return _execute_runtime(
        python_executable,
        cwd=directory,
        label="STANDARD_VENV",
        expected_root=venv_root,
    )


def verify(wheel: Path) -> dict[str, object]:
    errors: list[str] = []
    runtimes: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="tsao-wheel-runtime-") as temporary:
        directory = Path(temporary)
        target_payload, target_errors = _verify_target_install(wheel, directory)
        runtimes["PIP_TARGET"] = target_payload
        errors.extend(target_errors)

        venv_payload, venv_errors = _verify_standard_venv(wheel, directory)
        runtimes["STANDARD_VENV"] = venv_payload
        errors.extend(venv_errors)

    return {
        "wheel": str(wheel),
        "pass": not errors,
        "errors": errors,
        "runtimes": runtimes,
        "install_modes": ["PIP_TARGET", "STANDARD_VENV"],
        "import_origin_check": "ENFORCED",
        "standard_venv_isolation": "NO_SYSTEM_SITE_PACKAGES",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(_choose_wheel(args.wheel_dir))
    except (OSError, ValueError) as exc:
        result = {"pass": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
