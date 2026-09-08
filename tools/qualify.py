"""Run and record the scoped integration and source-regression qualification.

This intentionally does not label inherited full quality, performance, Windows
COM, commercial-solver or scientific qualifications as completed.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
import platform
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

STAGES = [
 ('integration', '.', ['tests']),
 ('aspen-status', 'components/aspen', ['tests/test_convergence.py','tests/test_backends_convergence.py']),
 ('research-quality', 'components/research', ['tests/test_scientific_quality.py','tests/test_scientific_contracts_v16.py']),
 ('computation-boundary', 'components/computation', ['tests/test_execution_boundary_contract.py']),
 ('dft-parser-geometry-quality', 'components/dft', ['skills/tsao-structure-prep/tests/test_neighbor_list.py','skills/tsao-dft-hpc-provenance/tests/test_engine_parser_contract.py','tests/test_quality_gate.py']),
 ('processing-estimation', 'components/processing', ['skills/poe/tests/test_poe_alpha7_reference.py']),
 ('reasoning-validators', 'skills/reasoning', ['open-deep-mind/tests/test_validators.py']),
]


EXTENDED_STAGES = [
 ('aspen-units-cache-hashing', 'components/aspen', ['tests/test_units.py','tests/test_units_hardening.py','tests/test_cache.py','tests/test_cache_write_efficiency.py','tests/test_hashing_hardening.py','tests/test_canonical_hash_single_source.py']),
 ('research-routing-evidence', 'components/research', ['tests/test_router.py','tests/test_semantic_scope.py','tests/test_claims.py','tests/test_strategy_quantitative_integrity.py','tests/test_receipts_capsules.py','tests/test_archive_safety.py']),
 ('computation-scientific-contracts', 'components/computation', ['tests/test_hashing_contract.py','tests/test_scientific_benchmarks.py','tests/test_confidence_model.py','tests/test_validation_fail_closed.py','tests/test_scientific_quantity_acceptance_contract.py']),
 ('dft-kinetics', 'components/dft', ['skills/tsao-dft-kinetics-multiscale/tests']),
 ('polymer-scientific-models', 'components/processing', ['skills/poe/tests/test_material_balance_v2.py','skills/poe/tests/test_numeric_contracts_v2.py','skills/poe/tests/test_polymer_metrics_v5.py','skills/poe/tests/test_poe_alpha7_edge_guards.py','skills/epdm/tests/test_epdm_reference.py','skills/epdm/tests/test_epdm_scalar_finite_hardening.py']),
]


def junit_counts(path: Path) -> dict[str, int]:
    data = path.read_bytes()
    if not data or len(data) > 10 * 1024 * 1024 or b"<!DOCTYPE" in data.upper():
        raise ValueError("invalid JUnit artifact")
    node = ET.fromstring(data)
    suites = [node] if node.tag == 'testsuite' else list(node.findall('testsuite'))
    if not suites:
        raise ValueError("JUnit has no suites")
    counts = {key: 0 for key in ('tests','failures','errors','skipped')}
    for suite in suites:
        for key in counts:
            value = suite.get(key)
            if value is None or not value.isdigit():
                raise ValueError("invalid JUnit count")
            counts[key] += int(value)
    if counts['tests'] == 0 or sum(counts[k] for k in ('failures','errors','skipped')) > counts['tests']:
        raise ValueError("JUnit has no tests or contradictory counts")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'.verification/qualification.json')
    parser.add_argument('--profile',choices=['integration','extended'],default='integration')
    args = parser.parse_args()
    run_id = uuid.uuid4().hex
    output = args.output.resolve()
    # Unique evidence directory: never reuse a previous invocation's XML.
    directory = output.parent/run_id
    directory.mkdir(parents=True,exist_ok=False)
    stages = STAGES + (EXTENDED_STAGES if args.profile == 'extended' else [])
    results = []
    for name,folder,files in stages:
        cwd = ROOT/folder
        env = os.environ.copy()
        env.update(PYTHONPATH=os.pathsep.join([str(ROOT),str(cwd),str(cwd/'src')]),
                   PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
                   OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        xml = directory/f'{name}.xml'
        command = [sys.executable,'-m','pytest',*files,'-q',f'--junitxml={xml}']
        started = time.monotonic()
        code,reason = 125,None
        try:
            with (directory/f'{name}.log').open('w',encoding='utf-8') as log:
                code = subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=600).returncode
        except subprocess.TimeoutExpired:
            code,reason = 124,'TIMEOUT'
        except OSError:
            reason = 'LAUNCH_FAILED'
        try:
            counts = junit_counts(xml)
        except (OSError,ValueError,ET.ParseError):
            counts,reason = None,'MISSING_OR_INVALID_TEST_EVIDENCE'
        ok = code == 0 and counts is not None and counts['failures'] == counts['errors'] == 0
        results.append({'name':name,'returncode':code,'ok':ok,'counts':counts,'reason':reason,
                        'seconds':round(time.monotonic()-started,3),'directory':str(directory.relative_to(output.parent))})
        print(f'{name}: {"PASS" if ok else "FAIL"}',flush=True)
    totals = {key:sum(row['counts'][key] for row in results if row['counts']) for key in ('tests','failures','errors','skipped')}
    ok = len(results) == len(stages) and all(row['ok'] for row in results)
    report = {'schema_version':'tsao.integration-qualification/2','run_id':run_id,
        'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),
        'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),'profile':args.profile,
        'python':platform.python_version(),'platform':platform.system(),'counts_including_subtests':totals,
        'scope':'root integration and explicitly named inherited software/scientific-reference tests',
        'state':'SCOPED_SOFTWARE_PASS' if ok else 'FAIL','stages':results,
        'full_inherited_qualification':'NOT_RUN_BY_THIS_PROFILE',
        'external_engine_execution':'NOT_EVALUATED','scientific_approval':'NOT_EVALUATED'}
    temporary = directory/'qualification.json.tmp'
    temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(output)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
