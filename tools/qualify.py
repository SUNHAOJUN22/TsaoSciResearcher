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


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'.verification/qualification.json')
    args=parser.parse_args()
    directory=args.output.resolve().parent
    directory.mkdir(parents=True,exist_ok=True)
    results=[]
    for name,folder,files in STAGES:
        cwd=ROOT/folder
        env=os.environ.copy()
        env['PYTHONPATH']=os.pathsep.join([str(ROOT),str(cwd),str(cwd/'src')])
        env['PYTHONDONTWRITEBYTECODE']='1'
        env['OPENBLAS_NUM_THREADS']='1'
        env['OMP_NUM_THREADS']='1'
        env['MKL_NUM_THREADS']='1'
        command=[sys.executable,'-m','pytest',*files,'-q',f'--junitxml={directory/name}.xml']
        started=time.monotonic()
        try:
            with (directory/f'{name}.log').open('w',encoding='utf-8') as log:
                completed=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,text=True,timeout=180)
            code=completed.returncode
        except subprocess.TimeoutExpired:
            code=124
        results.append({'name':name,'returncode':code,'seconds':round(time.monotonic()-started,3)})
        print(f'{name}: {"PASS" if code==0 else "FAIL"}',flush=True)
    ok=all(row['returncode']==0 for row in results)
    report={'schema_version':'tsao.integration-qualification/1','run_id':uuid.uuid4().hex,
            'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),
            'github_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
            'scope':'root integration and named inherited regression suites only',
            'state':'INTEGRATION_REGRESSION_PASS' if ok else 'FAIL', 'stages':results,
            'full_inherited_qualification':'NOT_RUN_BY_THIS_PROFILE',
            'external_engine_execution':'NOT_EVALUATED','scientific_approval':'NOT_EVALUATED'}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
