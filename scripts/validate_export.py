#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
ALLOWED={'.png','.svg','.pdf','.tif','.tiff'}
def main():
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+'); p.add_argument('--require-vector',action='store_true'); a=p.parse_args()
    try:
        files=[Path(x) for x in a.paths]
        for f in files:
            if not f.exists() or f.stat().st_size==0: raise ValueError(f'missing or empty export: {f}')
            if f.suffix.lower() not in ALLOWED: raise ValueError(f'unsupported figure extension: {f.suffix}')
        if a.require_vector and not any(f.suffix.lower() in {'.svg','.pdf'} for f in files): raise ValueError('vector export required')
        print(f'VALID exports={len(files)}')
    except Exception as e: print(f'INVALID: {e}',file=sys.stderr); raise SystemExit(1)
if __name__=='__main__': main()
