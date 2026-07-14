#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json
from collections import Counter
from common import ROOT
from capability_io import load_capabilities, capability_index

def main():
    p=argparse.ArgumentParser(); p.add_argument('--check',action='store_true'); a=p.parse_args()
    data=capability_index(); caps=load_capabilities()
    errors=[]
    if data.get('total')!=len(caps): errors.append('declared count mismatch')
    slugs=[c['slug'] for c in caps]
    if len(slugs)!=len(set(slugs)): errors.append('duplicate slugs')
    required={'id','slug','name_zh','name_en','category_zh','description_zh','workflow','inputs','outputs','risk_level','references'}
    for i,c in enumerate(caps):
        missing=required-set(c)
        if missing: errors.append(f'row {i}: missing {sorted(missing)}')
        if any(not str(c.get(k,'')).strip() for k in ['id','slug','name_zh','description_zh','workflow']): errors.append(f'row {i}: blank required value')
    if len(caps)<150: errors.append('fewer than 150 capabilities')
    csv_path=ROOT/'capability-index/capabilities.csv'
    if not csv_path.exists():
        errors.append('capabilities.csv is missing')
    else:
        with csv_path.open(encoding='utf-8-sig',newline='') as handle:
            csv_rows=list(csv.DictReader(handle))
        if len(csv_rows)!=len(caps): errors.append('capabilities.csv row count mismatch')
        if {r.get('slug') for r in csv_rows}!=set(slugs): errors.append('capabilities.csv slug set mismatch')
    stats={'total':len(caps),'by_category':dict(Counter(c['category_zh'] for c in caps)),'by_workflow':dict(Counter(c['workflow'] for c in caps))}
    if errors:
        print('\n'.join(errors)); raise SystemExit(1)
    print(json.dumps(stats,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
