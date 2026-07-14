#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
from common import ROOT
from capability_io import load_capabilities, capability_index
REQUIRED=['SKILL.md','README.md','README.zh-CN.md','README_EN.md','AGENTS.md','LICENSE','THIRD_PARTY.md','manifest.json','agents/openai.yaml','capability-index/capabilities.json','scripts/run_tests.py']
SECRET_PATTERNS=[re.compile(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}'),re.compile(r'sk-[A-Za-z0-9]{20,}')]
def main():
    errors=[]
    for rel in REQUIRED:
        if not (ROOT/rel).exists(): errors.append(f'missing {rel}')
    index=capability_index(); caps=load_capabilities()
    if index.get('total')!=158 or len(caps)!=158: errors.append('capability count must be 158')
    for p in ROOT.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.py','.md','.json','.yaml','.yml','.toml','.txt'}:
            text=p.read_text(encoding='utf-8',errors='ignore')
            marker='PLACEHOLDER' + '_CONTENT'
            if marker in text: errors.append(f'placeholder in {p.relative_to(ROOT)}')
            for pat in SECRET_PATTERNS:
                if pat.search(text): errors.append(f'possible secret in {p.relative_to(ROOT)}')
    if errors:
        print('\n'.join(errors),file=sys.stderr); raise SystemExit(1)
    print('structure validation PASS')
if __name__=='__main__': main()
