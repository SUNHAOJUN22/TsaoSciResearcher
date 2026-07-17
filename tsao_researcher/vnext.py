from __future__ import annotations
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
