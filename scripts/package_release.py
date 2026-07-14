#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, shutil, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',default='dist'); a=p.parse_args(); out=ROOT/a.out; out.mkdir(parents=True,exist_ok=True)
    version=(ROOT/'VERSION').read_text().strip(); zip_path=out/f'TsaoSciResearcher-v{version}.zip'
    files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and 'dist' not in p.parts]
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files): z.write(f,Path('TsaoSciResearcher')/f.relative_to(ROOT))
    h=hashlib.sha256(zip_path.read_bytes()).hexdigest(); (out/'SHA256SUMS').write_text(f'{h}  {zip_path.name}\n',encoding='utf-8')
    print(zip_path)
if __name__=='__main__': main()
