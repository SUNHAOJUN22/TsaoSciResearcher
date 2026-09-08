from __future__ import annotations
import copy
import hashlib
import json
import sqlite3
import threading
import urllib.request
import urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
import pytest
from tsao_science.core.canonical import digest
from tsao_science.core.jsonio import read_json, strict_loads, strict_dumps
from tsao_science.core.hashing import legacy_json_bytes, file_digest
from tsao_science.core.quantities import convert
from tsao_science.core.store import EvidenceStore
from tsao_science.contracts import validate_payload, payload_contracts, data_dependencies, enforce_lineage
from tsao_science.workspace import root, component_registry, component_paths
from tsao_science.engine import plan, run, verify_result
from tsao_science.verification import verify_record
from tsao_science.server import Handler


def test_single_component_owner_registry():
    rows = component_registry()
    assert set(rows) == {'research','computation','aspen','dft','processing','resindb','reasoning'}
    assert {k: root()/v['path'] for k,v in rows.items()} == component_paths()


@pytest.mark.parametrize('payload', [
    {}, {'question': True}, {'question': []}, {'question': 'x', 'shell': 'anything'},
    {'question': None}, {'question': 12}, {'question': 'x'*20001},
])
def test_bad_task_payload_rejected_before_execution(payload):
    spec = {'schema_version':'tsao.workflow/1','id':'bad','tasks':[
        {'id':'route','capability':'research.route','depends_on':[],'payload':payload}]}
    with pytest.raises(ValueError): plan(spec)


@pytest.mark.parametrize('cap,payload', [
    ('processing.first_order', {'times':[True], 'time_unit':'s','rate_constant':{'value':1,'unit':'1/s'}}),
    ('processing.first_order', {'times':[1], 'time_unit':'s','rate_constant':{'value':False,'unit':'1/s'}}),
    ('aspen.classify', {'messages':[], 'engine_idle':1, 'engine_returned':True}),
    ('materials.observation', {'observation':{'sample_id':'a','property':'x','source':'s','conditions':[], 'quantity':{'value':1,'unit':'1'},'evidence_kind':'reference'}}),
    ('dft.neighbors', {'coordinates':[[0,0]],'length_unit':'angstrom','cutoff':{'value':1,'unit':'angstrom'}}),
])
def test_boundaries_apply_to_all_domains(cap,payload):
    with pytest.raises(ValueError): validate_payload(cap,payload)


def test_preview_defers_data_references_but_worker_cannot():
    payload={'times':{'$ref':'parent.times_s'},'time_unit':'s','conversion':{'$ref':'parent.conversion'},'upper_rate':{'value':1,'unit':'1/s'}}
    validate_payload('processing.fit_first_order', payload, deferred=True)
    with pytest.raises(ValueError): validate_payload('processing.fit_first_order',payload)


def test_expected_quantity_kind_cannot_be_overridden():
    with pytest.raises(ValueError): convert({'value':1,'unit':'s','kind':'time'},'s',kind='length')


def test_utf16_wire_rejected():
    with pytest.raises(ValueError): strict_loads('{"x":1}'.encode('utf-16'))


@pytest.mark.parametrize('value', [{'中文':1}, {'n':1.0,'x':-0.0}, [1,True,None], {'nested':{'z':'\u2028'}}])
@pytest.mark.parametrize('ascii_mode',[True,False])
def test_legacy_identity_is_byte_compatible(value,ascii_mode):
    assert legacy_json_bytes(value,ensure_ascii=ascii_mode)==json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=ascii_mode,allow_nan=False).encode()


@pytest.mark.parametrize('size',[0,-1,True,1.5,2**40])
def test_file_hash_chunk_budget(tmp_path,size):
    with pytest.raises(ValueError):file_digest(tmp_path/'missing',chunk_size=size)


def test_file_hash_streamed(tmp_path):
    p=tmp_path/'data';p.write_bytes(b'abc'*10000)
    assert file_digest(p,chunk_size=7)==hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    work=tmp_path_factory.mktemp('records')
    result=run(read_json(root()/'examples/poe-reference-workflow.json'),work,allow_local=True)
    assert result['execution']=='SUCCEEDED',result.get('error')
    return read_json(result['result_file']),Path(result['result_file']),work/'evidence.sqlite3'


def reseal(record):
    record.pop('record_digest',None);record['record_digest']=digest(record);return record


def test_full_workflow_input_and_ledger_binding(completed):
    record,path,ledger=completed
    result=verify_result(path,ledger=ledger)
    assert result['workflow_binding']=='PASS'
    assert result['ledger_integrity']=='PASS'
    assert result['bound_tasks']==5
    assert result['source_authenticity']=='NOT_AUTHENTICATED'
    assert result['observations'][0]['evidence_kind']=='reference'


@pytest.mark.parametrize('mutation',['input','workflow','depends','capability','extra_task','validation','evidence_kind','external','approval','state'])
def test_resealed_inconsistent_record_is_rejected(completed,mutation):
    record=copy.deepcopy(completed[0])
    if mutation=='input':record['tasks']['fit']['input']['conversion'][0]=0.5
    elif mutation=='workflow':record['workflow']['tasks'][0]['payload']['question']='changed'
    elif mutation=='depends':record['tasks']['fit']['depends_on']=[]
    elif mutation=='capability':record['tasks']['fit']['capability']='dft.execute'
    elif mutation=='extra_task':record['tasks']['invented']=copy.deepcopy(record['tasks']['fit'])
    elif mutation=='validation':record['tasks']['fit']['validation']['state']='HOLD'
    elif mutation=='evidence_kind':record['tasks']['fit']['evidence_kind']='measured'
    elif mutation=='external':record['external_solver_executed']=True
    elif mutation=='approval':record['scientific_approval']='APPROVED'
    else:record['execution']='QUEUED'
    with pytest.raises(ValueError):verify_record(reseal(record))


def test_rehashed_record_cannot_claim_another_ledger_event(completed,tmp_path):
    record=copy.deepcopy(completed[0]);record['tasks']['fit']['event_digest']='0'*64
    path=tmp_path/'result.json';path.write_text(strict_dumps(reseal(record)))
    assert verify_result(path)['ledger_integrity']=='NOT_CHECKED'
    with pytest.raises(ValueError):verify_result(path,ledger=completed[2])


def test_verifier_never_creates_a_missing_database(completed,tmp_path):
    absent=tmp_path/'not-present.sqlite3'
    with pytest.raises(ValueError):verify_result(completed[1],ledger=absent)
    assert not absent.exists()


def test_later_ledger_appends_do_not_invalidate_earlier_checkpoint(completed):
    EvidenceStore(completed[2]).append({'other_run':'test'})
    assert verify_result(completed[1],ledger=completed[2])['ledger_integrity']=='PASS'


def test_read_only_store_cannot_append(completed):
    store=EvidenceStore(completed[2],readonly=True)
    with pytest.raises(PermissionError):store.append({'x':1})


@pytest.mark.parametrize('target',['measured','simulation'])
def test_reference_data_cannot_be_promoted(target):
    payload={'observation':{'evidence_kind':target}}
    with pytest.raises(ValueError):enforce_lineage('materials.observation',payload,{'calc':{'evidence_kind':'reference'}})


def test_ordering_dependency_is_not_a_data_derivation():
    assert data_dependencies({'x':{'$ref':'calc.a'},'y':[{'$ref':'calc.b'}]})=={'calc'}
    enforce_lineage('materials.observation',{'observation':{'evidence_kind':'measured'}},{})


def test_structure_to_material_observation(tmp_path):
    report=run(read_json(root()/'examples/structure-reference-workflow.json'),tmp_path,allow_local=True)
    assert report['execution']=='SUCCEEDED',report.get('error')
    assert report['tasks']['observation']['result']['observation']['quantity']['value']==2
    assert verify_result(Path(report['result_file']))['workflow_binding']=='PASS'


@pytest.fixture(scope='module')
def gateway():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join(5)


def test_gateway_reads_one_example_registry(gateway):
    with urllib.request.urlopen(gateway+'/api/science/examples',timeout=5) as response:
        result=json.load(response)
    assert {x['id'] for x in result['examples']}=={'poe','structure'}
    assert all(plan(x['workflow'])['execution']=='NOT_EXECUTED' for x in result['examples'])


def test_gateway_verifies_record_without_executing(gateway,completed):
    request=urllib.request.Request(gateway+'/api/science/verify',data=strict_dumps(completed[0]).encode(),
        headers={'Content-Type':'application/json','X-Tsao-Client':'workspace'})
    with urllib.request.urlopen(request,timeout=10) as response:result=json.load(response)
    assert result['integrity']=='PASS' and result['external_solver_executed'] is False
    assert result['ledger_integrity']=='NOT_CHECKED'


@pytest.mark.parametrize('endpoint',['execute','shell','run','ai/proxy'])
def test_gateway_cannot_execute(gateway,endpoint):
    request=urllib.request.Request(gateway+'/api/science/'+endpoint,data=b'{}',headers={'Content-Type':'application/json','X-Tsao-Client':'workspace'})
    with pytest.raises(urllib.error.HTTPError) as err:urllib.request.urlopen(request,timeout=5)
    assert err.value.code==404


def test_registry_schemas_are_available_for_frontend(gateway):
    with urllib.request.urlopen(gateway+'/api/science/contracts',timeout=5) as response:d=json.load(response)
    assert d['schema_version']=='tsao.payload-contracts/1'
    assert len(d['inputs'])==10 and len(d['outputs'])==8


def test_complete_catalog_is_federated_but_not_execution_authority():
    from tsao_science.catalog import catalog
    data=catalog()
    assert set(data['component_counts'])==set(component_registry())
    assert all(count>0 for count in data['component_counts'].values())
    assert data['component_counts']['research']==341
    assert data['component_counts']['computation']==164
    assert data['runtime_local_count']==8
    assert len({row['id'] for row in data['entries']})==data['total_records']
    assert all(row['execution']=='NOT_EVALUATED' for row in data['entries'])
    filtered=catalog(query='kinetic',owner='computation')
    assert filtered['matched_records']>0
    assert all(row['owner']=='computation' for row in filtered['entries'])


def test_junit_receipt_rejects_empty_and_missing_counts(tmp_path):
    from tools.qualify import junit_counts
    for content in ('<testsuites/>','<testsuite tests="1" failures="0" errors="0"/>','<testsuite tests="0" failures="0" errors="0" skipped="0"/>'):
        p=tmp_path/'bad.xml';p.write_text(content)
        with pytest.raises(ValueError):junit_counts(p)


def test_processing_flow_overflow_cannot_pass_a_balance():
    from tsao_science.adapters.local import _module
    module=_module('balance_a2','components/processing/tsao/scientific_contracts_v16.py')
    flow=module.Flow(1e308,'kg/s','mass',1e308)
    with pytest.raises(ValueError):flow.canonical()
    with pytest.raises(ValueError):module.component_balance({'x':flow},{'x':flow},atol=0,rtol=0)


def test_aspen_cache_discards_duplicate_and_overflow_json(tmp_path):
    import sys
    sys.path.insert(0,str(component_paths()['aspen']/'src'))
    from aspenops_nexus.cache import ResultCache
    cache=ResultCache(tmp_path/'cache.sqlite3')
    with sqlite3.connect(cache.path) as connection:
        connection.execute('INSERT INTO result_cache(cache_key,payload) VALUES (?,?)',('duplicate','{"x":1,"x":2}'))
        connection.execute('INSERT INTO result_cache(cache_key,payload) VALUES (?,?)',('overflow','{"x":1e999}'))
    assert cache.get_many(['duplicate','overflow'])=={}
