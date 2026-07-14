#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil
from datetime import datetime, timezone
from pathlib import Path
import yaml
from common import ROOT


def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def main():
    p=argparse.ArgumentParser(description='Initialize a traceable TsaoSciResearcher project')
    p.add_argument('--name',required=True); p.add_argument('--question',required=True)
    p.add_argument('--research-type',default='mixed',choices=['descriptive','explanatory','predictive','causal','design','mechanistic','mixed'])
    p.add_argument('--output',default='.'); p.add_argument('--force',action='store_true')
    a=p.parse_args(); root=Path(a.output).resolve()/'.tsao-research'
    if root.exists() and any(root.iterdir()) and not a.force: p.error(f'{root} exists; use --force')
    root.mkdir(parents=True,exist_ok=True)
    for d in ['figures','literature','data','reports','artifacts','protocols']:(root/d).mkdir(exist_ok=True)
    t=now(); pid='TSR-'+re.sub(r'[^A-Za-z0-9]+','-',a.name).strip('-')[:40] if False else 'TSR-'+datetime.now().strftime('%Y%m%d%H%M%S')
    project={'schema_version':'1.0','project_id':pid,'name':a.name,'created_at':t,'updated_at':t,'status':'proposed','scientific_question':a.question,'research_type':a.research_type,'scope':{'included':[],'excluded':[]},'hypotheses':[],'evidence_policy':{'material_claims_require_evidence':True,'inferences_require_assumptions':True},'approvals':[],'computation_handoffs':[]}
    (root/'project.yaml').write_text(yaml.safe_dump(project,sort_keys=False,allow_unicode=True),encoding='utf-8')
    for name,default in [('questions.json',{'questions':[]}),('hypotheses.json',{'hypotheses':[]}),('risks.json',{'risks':[]})]:
        (root/name).write_text(json.dumps(default,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name in ['evidence.jsonl','claims.jsonl','decisions.jsonl','artifacts.jsonl','approvals.jsonl']:(root/name).write_text('',encoding='utf-8')
    (root/'README.md').write_text('# Research state\n\nThis directory is managed by TsaoSciResearcher. Keep it under version control unless it contains sensitive data.\n',encoding='utf-8')
    print(root)

if __name__=='__main__':
    import re
    main()
