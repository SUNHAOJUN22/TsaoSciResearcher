"""Verify source preservation and explicitly declared edits without printing data records."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    source_map = json.loads((ROOT / 'migration/source-map.json').read_text(encoding='utf-8'))
    patches = json.loads((ROOT / 'migration/patches.json').read_text(encoding='utf-8'))
    edited = {item['target_path']: item for item in patches['changes']}
    failures = []
    count = 0
    seen = set()
    for source in source_map['sources']:
        for item in source['files']:
            count += 1
            name = item['target_path']
            if name in seen:
                failures.append('duplicate_destination')
            seen.add(name)
            path = ROOT / name
            if not path.is_file() or not path.resolve().is_relative_to(ROOT):
                failures.append('source_file_missing_or_outside_root')
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            expected = edited[name]['target_sha256'] if name in edited else item['source_sha256']
            if actual != expected:
                failures.append('undeclared_source_change')
    if len(source_map['sources']) != 7 or (ROOT / '.gitmodules').exists():
        failures.append('invalid_single_repository_inventory')
    result = {'schema_version': 'tsao.migration-verification/1', 'source_repositories': len(source_map['sources']),
              'preserved_source_files': count, 'declared_source_edits': len(edited),
              'errors': sorted(set(failures)), 'ok': not failures,
              'external_execution': 'NOT_EVALUATED', 'source_payloads_printed': False}
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
