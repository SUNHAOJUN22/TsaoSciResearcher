#!/usr/bin/env python3
"""Idempotent wrapper for the checksum-bound v0.6.0 finalizer."""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
base=ROOT/'scripts/finalize_v060_ci.py'
if version!='0.6.0':
    if not base.is_file(): raise SystemExit('canonical finalizer is missing')
    subprocess.run([sys.executable,str(base)],check=True)
# Remove every v0.6.0 one-shot control after materialization or verification.
for path in sorted((ROOT/'.github').rglob('*'),key=lambda p:len(p.parts),reverse=True):
    rel=path.relative_to(ROOT/'.github')
    remove=any(part.startswith('v060') or part.startswith('verify-finalize-v060') for part in rel.parts)
    remove=remove or (path.parent.name=='workflows' and (path.name.startswith('finalize-v060') or path.name.startswith('verify-finalize-v060') or path.name=='apply-v060-deep.yml'))
    if remove:
        if path.is_dir() and not path.is_symlink(): shutil.rmtree(path,ignore_errors=True)
        else: path.unlink(missing_ok=True)
for path in (ROOT/'scripts/finalize_v060_ci.py',ROOT/'scripts/finalize_v060_ci_v3.py'):
    path.unlink(missing_ok=True)
