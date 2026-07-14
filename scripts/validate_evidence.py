#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
import jsonschema
from common import ROOT, load_data, read_jsonl

def main():
    p=argparse.ArgumentParser(); p.add_argument('evidence_jsonl'); a=p.parse_args()
    schema=load_data(ROOT/'schemas/evidence-record.schema.json'); validator=jsonschema.Draft202012Validator(schema)
    try:
        rows=read_jsonl(a.evidence_jsonl); ids=set()
        for i,row in enumerate(rows,1):
            validator.validate(row)
            if row['evidence_id'] in ids: raise ValueError(f'duplicate evidence_id {row["evidence_id"]}')
            ids.add(row['evidence_id'])
            if row['source']['kind'] in {'paper','dataset','web','file','experiment','computation','instrument'} and not row['source']['locator'].strip(): raise ValueError(f'row {i}: source locator required')
        print(f'VALID evidence records={len(rows)}')
    except Exception as e: print(f'INVALID: {e}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
