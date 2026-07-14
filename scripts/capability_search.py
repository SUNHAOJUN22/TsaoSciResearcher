#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from common import ROOT
from capability_io import load_capabilities

def main():
    p=argparse.ArgumentParser(); p.add_argument('query'); p.add_argument('--workflow'); p.add_argument('--limit',type=int,default=20); a=p.parse_args()
    data=load_capabilities(); q=a.query.lower().strip(); results=[]
    for c in data:
        if a.workflow and c['workflow']!=a.workflow: continue
        hay=' '.join([c['slug'],c['name_zh'],c['name_en'],c['description_zh'],c['category_zh']]).lower()
        score=sum(2 if token in c['slug'] else 1 for token in q.split() if token in hay)
        if q in hay: score+=3
        if score: results.append((score,c))
    results.sort(key=lambda x:(-x[0],x[1]['slug']))
    print(json.dumps([{'score':s,'slug':c['slug'],'name_zh':c['name_zh'],'workflow':c['workflow'],'description':c['description_zh']} for s,c in results[:a.limit]],ensure_ascii=False,indent=2))
if __name__=='__main__': main()
