#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
import jsonschema
from common import ROOT, load_data, read_jsonl

def main():
    p=argparse.ArgumentParser(); p.add_argument('claims_jsonl'); p.add_argument('--evidence',required=True); a=p.parse_args()
    schema=load_data(ROOT/'schemas/claim.schema.json'); validator=jsonschema.Draft202012Validator(schema)
    try:
        evidence_ids={r['evidence_id'] for r in read_jsonl(a.evidence)}; claims=read_jsonl(a.claims_jsonl); ids=set()
        for row in claims:
            validator.validate(row)
            if row['claim_id'] in ids: raise ValueError(f'duplicate claim_id {row["claim_id"]}')
            ids.add(row['claim_id'])
            if row['claim_type'] in {'observation','calculation','sourced_fact'} and not row['evidence_ids']: raise ValueError(f'{row["claim_id"]}: evidence required')
            if row['claim_type']=='inference' and (not row['evidence_ids'] or not row['assumptions']): raise ValueError(f'{row["claim_id"]}: inference requires evidence and assumptions')
            missing=set(row['evidence_ids'])-evidence_ids
            if missing: raise ValueError(f'{row["claim_id"]}: unknown evidence IDs {sorted(missing)}')
        print(f'VALID claims={len(claims)}')
    except Exception as e: print(f'INVALID: {e}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
