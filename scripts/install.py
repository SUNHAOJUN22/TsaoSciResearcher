#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def destination(agent,scope,target):
    if target: return Path(target).expanduser().resolve()
    base=Path.cwd() if scope=='project' else Path.home()
    mapping={
      ('codex','user'):Path.home()/'.codex/skills/TsaoSciResearcher',('codex','project'):base/'.codex/skills/TsaoSciResearcher',
      ('claude','user'):Path.home()/'.claude/skills/TsaoSciResearcher',('claude','project'):base/'.claude/skills/TsaoSciResearcher',
      ('open-agent','user'):Path.home()/'.agents/skills/TsaoSciResearcher',('open-agent','project'):base/'.agents/skills/TsaoSciResearcher'}
    return mapping[(agent,scope)]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--agent',choices=['codex','claude','open-agent'],default='codex'); p.add_argument('--scope',choices=['user','project'],default='user'); p.add_argument('--target'); p.add_argument('--force',action='store_true'); p.add_argument('--dry-run',action='store_true'); p.add_argument('--uninstall',action='store_true'); p.add_argument('--validate',action='store_true'); a=p.parse_args()
    dst=destination(a.agent,a.scope,a.target)
    if a.uninstall:
        if a.dry_run: print(f'Would remove {dst}'); return
        if dst.exists(): shutil.rmtree(dst)
        print(f'Removed {dst}'); return
    if a.validate:
        ok=(ROOT/'SKILL.md').exists() and (ROOT/'manifest.json').exists() and (ROOT/'capability-index/capabilities.json').exists()
        if not ok: raise SystemExit('source validation failed')
    if dst.exists():
        if not a.force: p.error(f'{dst} exists; use --force')
        if not a.dry_run: shutil.rmtree(dst)
    if a.dry_run: print(f'Would install {ROOT} -> {dst}'); return
    ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache','dist','*.zip','.tsao-research')
    shutil.copytree(ROOT,dst,ignore=ignore)
    print(f'Installed TsaoSciResearcher to {dst}')
if __name__=='__main__': main()
