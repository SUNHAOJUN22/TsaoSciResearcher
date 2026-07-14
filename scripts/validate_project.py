#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import jsonschema
from common import ROOT, load_data

TRANSITIONS={
 'proposed':{'planned','rejected','superseded'},'planned':{'running','rejected','superseded'},'running':{'completed','rejected','superseded'},
 'completed':{'checked','rejected','superseded'},'checked':{'validated','rejected','superseded'},'validated':{'accepted','rejected','superseded'},
 'accepted':{'superseded'},'rejected':{'superseded'},'superseded':set()
}

def validate(path):
    data=load_data(path); schema=load_data(ROOT/'schemas/research-project.schema.json')
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(data)
    if data['status'] in {'validated','accepted'} and not data.get('hypotheses'):
        raise ValueError('validated/accepted project must record at least one hypothesis or explicit project rationale')
    return data

def main():
    p=argparse.ArgumentParser(); p.add_argument('project'); p.add_argument('--from-status'); a=p.parse_args()
    try:
        data=validate(a.project)
        if a.from_status and data['status'] not in TRANSITIONS.get(a.from_status,set()): raise ValueError(f'illegal transition {a.from_status} -> {data["status"]}')
        print(json.dumps({'valid':True,'project_id':data['project_id'],'status':data['status']},ensure_ascii=False))
    except Exception as e: print(f'INVALID: {e}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
