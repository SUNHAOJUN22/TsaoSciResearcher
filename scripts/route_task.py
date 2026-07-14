#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from common import ROOT


def normalize(text): return re.sub(r'\s+',' ',text.lower()).strip()

def route(text):
    rules=json.loads((ROOT/'router_rules.json').read_text(encoding='utf-8'))
    low=normalize(text); scores={}
    matches={}
    for wf,rule in rules.items():
        hit=[]; score=0
        for kw in rule['keywords']:
            if normalize(kw) in low:
                hit.append(kw); score += rule.get('weight',1) + max(0,len(kw.split())-1)
        scores[wf]=score; matches[wf]=hit
    ranked=sorted(scores,key=lambda x:(scores[x],x),reverse=True)
    best=ranked[0] if scores[ranked[0]]>0 else 'research-question'
    total=sum(scores.values())
    return {'workflow':best,'read_first':f'workflows/{best}/WORKFLOW.md','confidence':round(scores[best]/total,3) if total else 0.0,'matched':matches[best],'alternatives':[{'workflow':w,'score':scores[w]} for w in ranked[1:4] if scores[w]>0]}

def main():
    p=argparse.ArgumentParser(); p.add_argument('text',nargs='?'); p.add_argument('--json-file'); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test:
        cases={'请做系统综述并给出PRISMA流程':'systematic-review','画一张论文多panel图':'scientific-figure','设计样本量和随机化方案':'experiment-design','用GROMACS做分子动力学':'computation-handoff','检查论文是否存在引用误用':'research-integrity','写一份项目验收技术报告':'technical-report','帮我收敛研究问题':'research-question'}
        for text,want in cases.items():
            got=route(text)['workflow']; assert got==want,(text,got,want)
        print('router self-test PASS'); return
    text=a.text
    if a.json_file: text=json.loads(Path(a.json_file).read_text(encoding='utf-8'))['text']
    if not text: p.error('text or --json-file is required')
    print(json.dumps(route(text),ensure_ascii=False,indent=2))
if __name__=='__main__': main()
