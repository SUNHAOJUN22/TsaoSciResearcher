from __future__ import annotations
import copy
import hashlib
import json
import math
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from tsao_science.core.jsonio import strict_loads, strict_dumps, finite_real
from tsao_science.core.canonical import digest, canonical_bytes
from tsao_science.core.quantities import convert
from tsao_science.core.store import EvidenceStore
from tsao_science.engine import plan, execute_local, run, verify_result
from tsao_science.workspace import root

@pytest.mark.parametrize('text', ['{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', '{"x":1,"x":2}', '{"x":-Infinity}'])
def test_reject_invalid_json(text):
    with pytest.raises(ValueError): strict_loads(text)

@pytest.mark.parametrize('value',[True,False,float('nan'),float('inf'),'1',None])
def test_scientific_number_domain(value):
    with pytest.raises(ValueError): finite_real(value)

def test_cycles_and_depth():
    value=[];value.append(value)
    with pytest.raises(ValueError):strict_dumps(value)
    with pytest.raises(ValueError):strict_loads('['*70+'0'+']'*70)

def test_exact_binary64_contract():
    assert digest({'x':1})==digest({'x':1.0})
    assert digest({'x':-0.0})==digest({'x':0})
    assert digest({'b':2,'a':1})==digest({'a':1,'b':2})
    assert digest({'x':True})!=digest({'x':1})
    with pytest.raises(ValueError):digest(9007199254740993)

@pytest.mark.parametrize('quantity,target,expected',[
    ({'value':1,'unit':'min'},'s',60),
    ({'value':20,'unit':'degC'},'K',293.15),
    ({'value':0.9,'unit':'g/cm3'},'kg/m3',900),
    ({'value':6,'unit':'1/min'},'1/s',0.1),
])
def test_unit_conversions(quantity,target,expected):
    assert convert(quantity,target)==pytest.approx(expected)

@pytest.mark.parametrize('quantity,target',[
    ({'value':1},'s'),({'value':1,'unit':'kg/m3'},'s'),
    ({'value':0,'unit':'K'},'degC'),({'value':1,'unit':'bar'},'Pa'),
    ({'value':True,'unit':'s'},'min'),({'value':20,'unit':'degC'},'delta_K'),
])
def test_invalid_quantities(quantity,target):
    with pytest.raises(ValueError):convert(quantity,target)

def test_transactional_evidence(tmp_path):
    store=EvidenceStore(tmp_path/'events.sqlite3')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n:store.append({'n':n}),range(40)))
    assert store.verify()['verified_events']==40
    assert EvidenceStore(tmp_path/'events.sqlite3').verify()['verified_events']==40
    connection=sqlite3.connect(store.path)
    connection.execute('UPDATE events SET payload=? WHERE seq=0',('{"n":999}',));connection.commit();connection.close()
    with pytest.raises(ValueError):store.verify()

def fixture():return json.loads((root()/'examples/poe-reference-workflow.json').read_text())

def test_plan_is_detached():
    spec=fixture();ready=plan(spec)
    spec['tasks'][0]['payload']['question']='mutated'
    assert ready['tasks'][0]['payload']['question']!='mutated'
    assert ready['execution']=='NOT_EXECUTED'

@pytest.mark.parametrize('defect',['cycle','duplicate','reference','unknown','path','extra'])
def test_invalid_task_graphs(defect):
    spec=fixture()
    if defect=='cycle':spec['tasks'][0]['depends_on']=['fit']
    elif defect=='duplicate':spec['tasks'][1]['id']=spec['tasks'][0]['id']
    elif defect=='reference':spec['tasks'][2]['payload']['x']={'$ref':'observation.secret'}
    elif defect=='unknown':spec['tasks'][0]['capability']='shell.exec'
    elif defect=='path':spec['id']='../../bad'
    else:spec['tasks'][0]['shell']='rm -rf /'
    with pytest.raises(ValueError):plan(spec)

def test_authorization_is_separate(tmp_path):
    with pytest.raises(PermissionError):run(fixture(),tmp_path)
    with pytest.raises(ValueError):execute_local('aspen.execute',{})

def test_actual_cross_component_pipeline(tmp_path):
    result=run(fixture(),tmp_path,allow_local=True)
    assert result['execution']=='SUCCEEDED',result.get('error')
    assert len(result['tasks'])==5
    assert result['tasks']['fit']['result']['rate_constant_s']==pytest.approx(0.1,rel=1e-8)
    assert result['scientific_approval']=='NOT_EVALUATED'
    assert result['external_solver_executed'] is False
    path=Path(result['result_file'])
    assert verify_result(path)['integrity']=='PASS'
    data=json.loads(path.read_text());data['tasks']['fit']['result']['rate_constant_s']=999
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):verify_result(path)

def test_same_units_same_physics():
    a=execute_local('processing.first_order',{'times':[0,60],'time_unit':'s','rate_constant':{'value':0.1,'unit':'1/s'}})
    b=execute_local('processing.first_order',{'times':[0,1],'time_unit':'min','rate_constant':{'value':6,'unit':'1/min'}})
    assert a==b


@pytest.mark.parametrize('message', ['not successful', 'failed', 'unknown'])
def test_explicit_domain_failure_stops_dependents(tmp_path, message):
    spec = {'schema_version': 'tsao.workflow/1', 'id': 'StopOnFailure', 'tasks': [
        {'id': 'check', 'capability': 'aspen.classify', 'depends_on': [],
         'payload': {'messages': [message], 'engine_idle': True, 'engine_returned': True}},
        {'id': 'next', 'capability': 'processing.first_order', 'depends_on': ['check'],
         'payload': {'times': [1, 2], 'time_unit': 's', 'rate_constant': {'value': 0.1, 'unit': '1/s'}}},
    ]}
    record = run(spec, tmp_path, allow_local=True)
    assert record['execution'] == 'FAILED'
    assert set(record['tasks']) == {'check'}
    assert record['tasks']['check']['execution'] == 'SUCCEEDED'
    assert record['tasks']['check']['validation']['state'] in {'FAIL', 'HOLD'}
    assert record['scientific_approval'] == 'NOT_EVALUATED'
