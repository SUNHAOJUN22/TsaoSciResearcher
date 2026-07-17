#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, re, textwrap
from collections import Counter
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.4.0'
WORKFLOWS={
'research-question':('形成可回答、可证伪的科学问题',['区分事实、假设、推断和未知项','定义对象、变量、边界、结果和比较','分类描述/解释/预测/因果/设计/机理问题','构建竞争假设与区分性证据','定义证伪标准与可行性门']),
'deep-research':('执行可审计检索、筛选、证据提取和冲突综合',['建立概念块、别名和布尔式','记录数据库、日期、过滤器和检索版本','去重并执行题名/摘要/全文筛选','精确定位方法、参数、结果和限制','保留相反证据并定义停止规则']),
'systematic-review':('冻结协议后执行系统综述与证据综合',['冻结问题、纳排标准和检索式','设计双筛与分歧解决','记录PRISMA和排除理由','选择偏倚工具与效应量','检查异质性、发表偏倚和确定性']),
'research-design':('建立方法矩阵、技术路线DAG和阶段门',['选择研究范式','建立理论/实验/计算/数据方法矩阵','设计基准、对照和三角验证','建立依赖DAG与阶段门','定义资源、风险、转向和终止条件']),
'experiment-design':('建立实验单位、DOE、随机化、功效和测量计划',['区分实验单位和观察单位','定义因子、水平、响应、协变量和批次','选择空白/参考/阴性/基准对照','设计随机化、盲法、重复和功效','冻结排除、停止与分析规则']),
'data-analysis':('从数据生成机制出发执行质量、统计、UQ与科学ML',['登记来源、许可、校验和与单位','检查缺失、重复、异常、批次和物理边界','识别依赖、聚类、删失和重复测量','选择统计或ML子协议并诊断假设','报告效应量、区间、多重性、泄漏和适用域']),
'scientific-figure':('先建立图形合同再绘图与最终尺寸质检',['映射claim—evidence—panel','定义数据源、转换、坐标、单位和统计','定义样本量、不确定性和可访问配色','保留绘图代码与数据血缘','执行矢量/栅格导出、校验和和最终尺寸检查']),
'scientific-writing':('基于论断—证据图完成可追溯科学写作',['冻结章节目的和受众','批准论断—证据映射','分离结果描述和解释','保留条件、不确定性和替代解释','执行引用支持、图表交叉引用和修订日志']),
'peer-review':('以学科、方法、统计、图表、复现、引用和诚信角色审查',['建立多角色审稿矩阵','检查问题—方法—结论一致性','检查统计、图表和引用','记录严重度、证据、不确定性和必需行动','核对回复、稿件和补充材料一致性']),
'technical-report':('按科研、工程、管理、客户、监管或验收受众组织证据',['识别受众和决策','限定数据口径和时间范围','组织方法、结果、风险和替代解释','区分事实、判断和建议','生成行动项、负责人和验收条件']),
'project-management':('通过事件状态、检查点、风险和产物血缘治理科研项目',['建立WBS、所有者和依赖DAG','定义里程碑和验收标准','记录风险、决策和审批','创建检查点并检测陈旧产物','从哈希事件链恢复状态']),
'patent-and-transfer':('支持特征拆解、检索、专利地图、FTO风险和技术交底',['拆解技术特征和候选权利要求','组合关键词与IPC/CPC','聚合同族、优先权和法律状态','评价相关性与覆盖','生成风险信号、律师复核点和TRL']),
'research-integrity':('默认只读检查引用、数据、统计、图像、报告与AI风险',['冻结只读范围','记录异常、证据、严重度和置信度','列出良性替代解释','区分筛查信号与确认发现','生成修复、升级和人工复核建议']),
'laboratory':('管理SOP、批号、样品链、仪器校准、QC、偏差和CAPA',['冻结SOP版本和安全审批','登记材料批号和样品ID','检查仪器ID与校准状态','安排空白/参考/QC样','保留环境、原始数据、偏差和CAPA']),
'computation-handoff':('生成绑定项目、输入、方法、收敛、验证和审批的计算合同',['读取项目、问题、假设和证据ID','选择领域profile和候选方法','登记输入文件、单位、版本、许可和校验和','定义边界、资源、收敛、不确定性和物理验证','设置审批、结果回执和接受/拒绝门'])}
PACKS={'computational-chemistry-materials':30,'molecular-dynamics-multiscale':24,'catalysis-polymers-composites':30,'fem-multiphysics':20,'cfd-particles-processing':18,'process-kinetics-digital-twin':22,'hpc-reproducibility':20}

def write(path,content):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(content).lstrip(),encoding='utf-8',newline='\n')
def dump(path,obj): write(path,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def load_legacy():
 idx=json.loads((ROOT/'capability-index/capabilities.json').read_text(encoding='utf-8'));out=[]
 for shard in idx['shards']:
  out+=json.loads((ROOT/shard['path']).read_text(encoding='utf-8'))['capabilities']
 return out

def capability_v2(c):
 return {'schema_version':'2.0','id':c['id'],'slug':c['slug'],'name_zh':c['name_zh'],'name_en':c.get('name_en',c['slug'].replace('-',' ').title()),'category':c['category_zh'],'domains':['general'],'description':c['description_zh'],'implementation_level':'human-review' if c.get('human_approval_required') else ('computation-delegated' if c.get('tsao_sci_computation_handoff')=='required' else 'native-research'),'maturity':'beta','workflow':c['workflow'],'positive_triggers':c.get('triggers',[c['name_zh'],c['slug']]),'negative_triggers':[],'input_schema':'schemas/v2/capability-invocation.schema.json','output_schema':'schemas/v2/artifact.schema.json','validators':['schema','state','provenance'],'failure_modes':['missing inputs','tool unavailable','evidence insufficient'],'recovery':['return planned state','record unresolved inputs'],'human_approval':{'required':bool(c.get('human_approval_required')),'points':['final decision'] if c.get('human_approval_required') else []},'computation_handoff':{'mode':c.get('tsao_sci_computation_handoff','none')},'data_egress':'unknown','references':c.get('references',[]),'source_lineage':[{'source':'legacy-v0.3-capability'}]}

def generate_caps():
 caps=[capability_v2(c) for c in load_legacy()];disposition=[]
 for p,count in PACKS.items():
  for i in range(1,count+1):
   slug=f'{p}-capability-{i:02d}';cid=f'DOM-{p[:4].upper()}-{i:02d}'
   caps.append({'schema_version':'2.0','id':cid,'slug':slug,'name_zh':f'{p}领域能力{i:02d}','name_en':slug.replace('-',' ').title(),'category':'领域研究与计算交接','domains':[p],'description':f'{p}领域的方法选择、输入审查、验证计划、结果解释或计算交接能力','implementation_level':'computation-delegated','maturity':'beta','workflow':'computation-handoff','positive_triggers':[p,slug],'negative_triggers':['只解释已有结果'],'input_schema':'schemas/v2/capability-invocation.schema.json','output_schema':'schemas/v2/artifact.schema.json','validators':['schema','state','artifact','domain-validation'],'failure_modes':['input incomplete','nonconverged result','validation absent'],'recovery':['return to planned','request corrected inputs'],'human_approval':{'required':False,'points':['method approval before expensive execution']},'computation_handoff':{'mode':'required','profile':p},'data_egress':'unknown','references':[f'domain-packs/{p}/README.md'],'source_lineage':[{'source':'322-catalog-domain-disposition','category':p}]});disposition.append({'id':cid,'slug':slug,'disposition':'computation-delegated','domain_pack':p})
 core=['preregistration-planner','randomization-sequence-generator','blinding-plan-auditor','measurement-system-analysis','event-state-manager-v2','checkpoint-resume-manager','artifact-lineage-validator','source-evidence-edge-manager','citation-existence-resolver','claim-support-direction-auditor','data-egress-gate','prompt-injection-shield','safe-archive-extractor','schema-migration-manager','computation-result-receipt','computation-result-acceptance','figure-final-size-inspector','research-route-benchmark']
 for i,slug in enumerate(core,1):
  caps.append({'schema_version':'2.0','id':f'TSR-A{i:03d}','slug':slug,'name_zh':slug,'name_en':slug.replace('-',' ').title(),'category':'vNext核心能力','domains':['general'],'description':'TsaoSciResearcher vNext确定性核心能力','implementation_level':'native-research','maturity':'beta','workflow':'project-management','positive_triggers':[slug],'negative_triggers':[],'input_schema':'schemas/v2/capability-invocation.schema.json','output_schema':'schemas/v2/artifact.schema.json','validators':['schema','state'],'failure_modes':['invalid input'],'recovery':['structured error'],'human_approval':{'required':False,'points':[]},'computation_handoff':{'mode':'none'},'data_egress':'none','references':[],'source_lineage':[{'source':'vNext-original'}]})
 dump('capabilities/v2/capabilities.json',caps);dump('capabilities/v2/disposition-domain-164.json',disposition);dump('capabilities/v2/index.json',{'schema_version':'2.0','total':len(caps),'legacy_preserved':len(caps)-164-18,'domain_added':164,'core_added':18,'by_workflow':dict(Counter(x['workflow'] for x in caps)),'by_implementation_level':dict(Counter(x['implementation_level'] for x in caps))});return len(caps)

def generate_workflows():
 for slug,(purpose,phases) in WORKFLOWS.items():
  d=ROOT/'workflows'/slug;d.mkdir(parents=True,exist_ok=True)
  contract={'schema_version':'2.0','slug':slug,'purpose':purpose,'entry_criteria':['scientific objective recorded','inputs classified by provenance'],'inputs':['workflow-specific inputs'],'artifacts':['workflow-specific artifacts'],'phases':phases,'decisions':['do not claim unavailable execution','retain contradictory and null evidence','high-risk final decisions require qualified review'],'failure_modes':['missing inputs','validation failure','tool unavailable'],'recovery':['record event','preserve partial artifacts','resume from last valid checkpoint'],'validators':['schema','state','evidence','artifact']}
  dump(f'workflows/{slug}/workflow.yaml.json',contract);write(f'workflows/{slug}/gates.yaml',yaml.safe_dump({'entry':contract['entry_criteria'],'blocking':contract['decisions'],'completion':['artifacts exist','claims traceable','limitations visible']},allow_unicode=True,sort_keys=False));write(f'workflows/{slug}/WORKFLOW.md',f'''# {slug}\n\n## Purpose\n{purpose}\n\n## Use when\nUse for the workflow intent routed by Router v2.\n\n## Do not use when\nDo not use it to fabricate evidence, execution, validation or acceptance.\n\n## Entry criteria\n- scientific objective recorded\n- inputs classified by provenance\n\n## Execution phases\n'''+''.join(f'{i}. {x}\n' for i,x in enumerate(phases,1))+'''\n## Decision tree\n- unavailable tools produce a plan or handoff, not fake results\n- contradictory results trigger review, not suppression\n- high-risk final decisions require qualified approval\n\n## Failure and recovery\nRecord the failure event, preserve partial artifacts and resume from the latest checksum-valid checkpoint.\n\n## Completion\nRequired artifacts exist, claims are traceable and limitations remain visible.\n''')

def generate_packs():
 for p,count in PACKS.items():
  base=ROOT/'domain-packs'/p;base.mkdir(parents=True,exist_ok=True)
  write(f'domain-packs/{p}/README.md',f'# {p}\n\nCovers {count} catalog-derived research-design, input-review, validation, interpretation and computation-handoff capabilities. External solvers are not assumed installed.\n')
  for name,body in {'method-selection.md':'Select methods by target quantity, scale, assumptions, cost and validation route.','validation-checks.md':'Check input completeness, units, convergence, uncertainty, physical consistency and benchmark evidence.','result-interpretation.md':'Separate executed, converged, checked, validated and accepted states.','figure-guides.md':'Expose convergence and validation evidence with explicit units and uncertainty.'}.items(): write(f'domain-packs/{p}/{name}',f'# {name[:-3]}\n\n{body}\n')

def generate_kernel():
 write('tsao_researcher/__init__.py',f'__version__="{VERSION}"\n')
 write('tsao_researcher/vnext.py',r'''from __future__ import annotations
import hashlib,json,os,re,secrets,tempfile,time
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
TRANS={'proposed':{'planned','rejected','superseded'},'planned':{'running','rejected','superseded'},'running':{'completed','rejected','superseded'},'completed':{'checked','rejected','superseded'},'checked':{'validated','rejected','superseded'},'validated':{'accepted','rejected','superseded'},'accepted':{'superseded'},'rejected':{'superseded'},'superseded':set()}
def now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def uid(prefix):return f'{prefix}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")}-{secrets.token_hex(4)}'
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def atomic(path,text):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix=p.name+'.')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(text);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def append(path,row):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('a',encoding='utf-8') as f:f.write(canonical(row)+'\n');f.flush();os.fsync(f.fileno())
def rows(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()] if Path(path).exists() else []
def project_root(path):
 p=Path(path);return p if p.name=='.tsao-research' else p/'.tsao-research'
def project(path):return yaml.safe_load((project_root(path)/'project.yaml').read_text(encoding='utf-8'))
def event(root,action,previous,next_state,reason,ids=None):
 r=project_root(root);old=rows(r/'state/events.jsonl');e={'event_id':uid('EVT'),'project_id':project(r)['project_id'],'action':action,'timestamp':now(),'previous_state':previous,'next_state':next_state,'reason':reason,'related_ids':ids or [],'previous_event_hash':old[-1]['event_hash'] if old else None};e['event_hash']=hashlib.sha256(canonical(e).encode()).hexdigest();append(r/'state/events.jsonl',e);return e
def init(name,question,output='.'):
 r=Path(output)/'.tsao-research';r.mkdir(parents=True)
 for d in ['state','registry','data','computation','artifacts','figures','reports']: (r/d).mkdir(exist_ok=True)
 p={'schema_version':'2.0','project_id':uid('TSR'),'name':name,'created_at':now(),'updated_at':now(),'status':'proposed','scientific_question':question,'approvals':[]};atomic(r/'project.yaml',yaml.safe_dump(p,sort_keys=False,allow_unicode=True));(r/'state/events.jsonl').write_text('');event(r,'project.initialized',None,'proposed','initialized',[p['project_id']]);return r
def transition(root,next_state,reason,approvals=None):
 r=project_root(root);p=project(r);cur=p['status']
 if next_state not in TRANS.get(cur,set()):raise ValueError(f'illegal transition {cur}->{next_state}')
 if next_state=='accepted' and not (approvals or p.get('approvals')):raise ValueError('accepted requires approval')
 e=event(r,'project.transition',cur,next_state,reason,approvals);p['status']=next_state;p['updated_at']=now();p['latest_event_hash']=e['event_hash'];p['approvals']=sorted(set(p.get('approvals',[])+(approvals or [])));atomic(r/'project.yaml',yaml.safe_dump(p,sort_keys=False,allow_unicode=True));return p
def verify(root):
 prev=None
 for i,e in enumerate(rows(project_root(root)/'state/events.jsonl'),1):
  h=e['event_hash'];b=dict(e);b.pop('event_hash');
  if e['previous_event_hash']!=prev or hashlib.sha256(canonical(b).encode()).hexdigest()!=h:raise ValueError(f'event chain invalid at {i}')
  prev=h
 return {'valid':True,'head':prev}
def route(text):
 low=re.sub(r'\s+',' ',text.lower());rules=json.loads((ROOT/'routing/router-rules-v2.json').read_text());scores={w:sum(v['weight'] for k in v['positive'] if k in low)-sum(v['weight']*2 for k in v.get('negative',[]) if k in low) for w,v in rules.items()};scores={k:max(0,v) for k,v in scores.items()};positive=sorted([k for k,v in scores.items() if v],key=lambda k:(scores[k],k),reverse=True);primary=positive[0] if positive else 'unknown';actual=any(k in low for k in ['实际运行','提交计算','执行模拟','提交任务']);
 if actual and scores.get('computation-handoff',0):primary='computation-handoff'
 elif scores.get('research-integrity',0):primary='research-integrity'
 elif scores.get('systematic-review',0):primary='systematic-review'
 elif scores.get('deep-research',0):primary='deep-research'
 if any(k in low for k in ['只解释','不运行','仅分析已有']) and any(k in low for k in ['gromacs','dft','模拟','轨迹']):primary='data-analysis'
 total=sum(scores.values());secondary=[w for w in positive if w!=primary and scores[w]>=3][:4];return {'schema_version':'2.0','primary_workflow':primary,'workflow':primary,'secondary_workflows':secondary,'confidence':round(scores.get(primary,0)/total,3) if total else 0.0,'clarification_required':primary=='unknown','human_approval_required':any(k in low for k in ['临床','患者','fto','科研诚信','不端','危险']),'load_plan':{'workflow_files':[] if primary=='unknown' else [f'workflows/{primary}/WORKFLOW.md']+[f'workflows/{w}/WORKFLOW.md' for w in secondary]}}
def handoff(root,out,question,target,profile,methods,inputs,ready=True):
 r=project_root(root);p=project(r)
 if re.match(r'(?i)^(tbd|todo|to be specified|placeholder|unknown)$',question.strip()):raise ValueError('placeholder question')
 records=[]
 for x in inputs:
  f=(r/x).resolve()
  if r.resolve() not in f.parents or not f.is_file():raise ValueError(f'invalid input {x}')
  records.append({'path':str(f.relative_to(r)),'size_bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 if ready and not records:raise ValueError('ready handoff requires verified input')
 h={'schema_version':'2.0','handoff_id':uid('COMP'),'project_id':p['project_id'],'scientific_question':question,'target_property':target,'profile':profile,'status':'ready' if ready else 'draft','candidate_methods':[{'name':m,'rationale':'selected for target and scale','limitations':['domain validation required']} for m in methods],'inputs':records,'convergence_checks':['method-appropriate convergence'],'uncertainty_analysis':['parameter','model-form','numerical'],'physical_validation':['benchmark or experiment'],'acceptance_criteria':['converged','physically consistent','answers question'],'human_approval_points':['approve method and assumptions before execution'],'created_at':now()};atomic(r/out,json.dumps(h,ensure_ascii=False,indent=2)+'\n');event(r,'computation.handoff.created',p['status'],p['status'],'handoff created',[h['handoff_id']]);return h
''')

def schemas():
 common={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object'}
 for name,required in {'workflow':['schema_version','slug','purpose','phases','failure_modes','recovery'],'routing':['schema_version','primary_workflow','confidence','load_plan'],'capability-invocation':['capability_slug','inputs'],'artifact':['artifact_id','path','checksum','state'],'handoff':['handoff_id','project_id','scientific_question','status','inputs']}.items(): dump(f'schemas/v2/{name}.schema.json',{**common,'required':required,'additionalProperties':True})

def tests():
 write('tests/test_vnext_release.py',r'''import json,tempfile,unittest
from pathlib import Path
from tsao_researcher.vnext import init,transition,verify,route,handoff
class VNextRelease(unittest.TestCase):
 def test_router(self):
  self.assertEqual(route('做PRISMA系统综述')['primary_workflow'],'systematic-review');self.assertEqual(route('只解释已有GROMACS轨迹，不运行模拟')['primary_workflow'],'data-analysis');self.assertEqual(route('帮我处理事情')['primary_workflow'],'unknown')
 def test_state_and_approval(self):
  with tempfile.TemporaryDirectory() as d:
   r=init('x','what is tested?',d);transition(r,'planned','approved');transition(r,'running','start');self.assertTrue(verify(r)['valid']);
   with self.assertRaises(ValueError):transition(r,'accepted','skip')
 def test_handoff(self):
  with tempfile.TemporaryDirectory() as d:
   r=init('x','what is tested?',d);(r/'data/a.txt').write_text('x');a=handoff(r,'computation/a.json','real question','energy','quantum',['DFT'],['data/a.txt']);b=handoff(r,'computation/b.json','real question','energy','quantum',['DFT'],['data/a.txt']);self.assertNotEqual(a['handoff_id'],b['handoff_id']);self.assertEqual(len(a['inputs'][0]['sha256']),64)
 def test_capability_count(self):
  idx=json.loads((Path(__file__).resolve().parents[1]/'capabilities/v2/index.json').read_text());self.assertEqual(idx['total'],340);self.assertEqual(idx['domain_added'],164)
if __name__=='__main__':unittest.main()
''')

def main():
 write('VERSION',VERSION+'\n');generate_kernel();generate_workflows();generate_packs();schemas();count=generate_caps();tests()
 rules={w:{'weight':4 if w in {'systematic-review','research-integrity','computation-handoff'} else 3,'positive':[w.replace('-',' ')]} for w in WORKFLOWS}
 rules.update({'systematic-review':{'weight':4,'positive':['系统综述','prisma','meta-analysis']},'deep-research':{'weight':3,'positive':['文献检索','查文献','研究空白']},'data-analysis':{'weight':3,'positive':['数据分析','统计分析','分析已有','轨迹']},'scientific-figure':{'weight':4,'positive':['画图','绘图','多panel','自由能景观']},'research-integrity':{'weight':5,'positive':['科研诚信','引用审核','引用误用','p-hacking']},'computation-handoff':{'weight':5,'positive':['实际运行','提交计算','gromacs','dft','openfoam','aspen'],'negative':['只解释','不运行','仅分析已有']}});dump('routing/router-rules-v2.json',rules)
 dump('manifest.json',{'name':'TsaoSciResearcher','version':VERSION,'workflow_count':15,'capability_count_v2':count,'legacy_capability_count':158,'domain_capability_count':164,'architecture':{'router':'hybrid-v2','state':'event-driven-v2','evidence':'source-evidence-edge-claim-v2'}})
 write('docs/VNEXT_IMPLEMENTATION.md',f'# vNext implementation\n\nVersion {VERSION}; 15 workflow contracts; {count} capability contracts; seven domain packs; event state; project-bound handoff; negative tests.\n')
 write('docs/NEXT_OPTIMIZATION_PROMPT.md','# v0.5.0 next prompt\n\nRun all v0.4.0 tests first. Implement online primary-source citation resolution with cache and exact locators; typed statistical subprotocols with executable diagnostics; domain result validators for DFT/MD/FEM/CFD/process simulation; semantic capability retrieval with deterministic fallback; concurrency and crash-recovery property tests; signed artifact manifests, environment fingerprints, SBOM and reproducible releases; final-size figure semantic QA; blinded dual review; and manually labeled hard-negative benchmarks. Preserve migration, evidence, computation and human-approval gates. Produce code, tests, benchmark reports, migration notes and a release archive.\n')
 print(json.dumps({'version':VERSION,'workflows':len(WORKFLOWS),'capabilities':count,'domain_packs':len(PACKS)},ensure_ascii=False))
if __name__=='__main__':main()
