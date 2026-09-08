from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path
import pytest
from tsao_science.workspace import root
from tsao_science.engine import execute_local
from tsao_science.adapters.local import _module

@pytest.mark.parametrize('text,expected',[
    ('not successful','not_converged'),('not successfully completed','not_converged'),
    ('0 errors; completed successfully','converged'),('errors: 0; converged','converged'),
    ('not converged','not_converged'),('unsuccessful','not_converged'),
    ('not ok','not_converged'),('idle','unknown'),('fatal error','not_converged'),
])
def test_aspen_status(text,expected):
    result=execute_local('aspen.classify',{'messages':[text],'engine_idle':True,'engine_returned':True})
    assert result['state']==expected
    assert result['external_solver_executed'] is False

def test_finite_geometry_overflow_is_rejected():
    module=_module('fix_neighbors', 'components/dft/skills/tsao-structure-prep/scripts/neighbor_list.py')
    for backend in (module.reference_pairs,module.numpy_pairs,module.cell_list_pairs):
        with pytest.raises(ValueError):backend([[0,0,0],[1e308,0,0]],1e200)

def test_small_conversion_and_fixed_time_identifiability():
    module=_module('fix_estimation','components/processing/skills/poe/estimation.py')
    assert module.first_order_conversion([1e-20],1)[0]==pytest.approx(1e-20,rel=1e-12,abs=0)
    observations=module.first_order_conversion([10,10,10],0.1)
    fit=module.fit_first_order_rate([10,10,10],observations,upper_s=1)
    assert fit['identifiable'] is True
    assert fit['time_design_spans_interval'] is False
    assert fit['scientific_approval']=='NOT_EVALUATED'
    rank=module.assess_identifiability([[0,0],[0,0]])
    assert rank['condition_number'] is None
    json.dumps(rank,allow_nan=False)

def test_computation_legacy_format_stays_finite_and_strict():
    sys.path.insert(0,str(root()/'components/computation'))
    from tsao_computation.execution_boundary import _canonical
    assert _canonical({'x':1})==b'{"x":1}'
    with pytest.raises(ValueError):_canonical({'x':float('nan')})

@pytest.mark.parametrize('design',['non-randomized observational study','not randomized','非随机观察研究','没有干预'])
def test_research_design_negation(design):
    sys.path.insert(0,str(root()/'components/research'))
    from tsao_researcher.scientific_quality import _affirmed_experimental_design
    assert _affirmed_experimental_design(design) is False

def test_research_design_affirmed():
    sys.path.insert(0,str(root()/'components/research'))
    from tsao_researcher.scientific_quality import _affirmed_experimental_design
    assert _affirmed_experimental_design('randomized controlled experiment') is True

def test_ledger_json_type_and_deep_graph():
    module=_module('fix_ledger','skills/reasoning/open-deep-mind/scripts/validate_ledger.py')
    assert module.validate({'claims':[{'id':'D1','type':[],'claim':'x','status':{},'scope':'x','falsifier':'x'}]})
    graph={f'N{i}':{f'N{i+1}'} for i in range(3000)};graph['N3000']=set()
    assert module.find_cycles(graph)==[]
    graph['N3000']={'N0'}
    assert len(module.find_cycles(graph))==1

def test_dft_dynamic_digest_is_runtime_validated(tmp_path):
    module=_module('fix_parser','components/dft/skills/tsao-dft-hpc-provenance/scripts/engine_parser_contract.py')
    path=tmp_path/'input';path.write_text('x')
    assert len(module.sha256_file(path))==64
    original=module._SCAN.sha256_file
    try:
        module._SCAN.sha256_file=lambda *a,**kw:True
        with pytest.raises(TypeError):module.sha256_file(path)
    finally:module._SCAN.sha256_file=original

def test_preflight_not_software_qualification():
    module=_module('fix_preflight','components/dft/scripts/build_release_acceptance.py')
    assert module.SOFTWARE_READY=='SOFTWARE_PREFLIGHT_READY'
