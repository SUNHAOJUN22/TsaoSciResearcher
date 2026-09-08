"""Owner-side retirement audit; no deletion and no embedded credentials.

Default mode is read-only. --archive requires a locally authenticated GitHub CLI
with Administration permission for all six legacy repositories. This tool is not
called by CI and never reports that an API operation succeeded without readback.
"""
from __future__ import annotations
import argparse
import base64
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = 'SUNHAOJUN22/TsaoSciResearcher'


def api(endpoint: str, payload: dict | None = None) -> object:
    command = ['gh','api',endpoint]
    text = None
    if payload is not None:
        command += ['--method','PATCH','--input','-']
        text = json.dumps(payload)
    completed = subprocess.run(command,input=text,text=True,encoding='utf-8',
                               capture_output=True,timeout=60,check=False)
    if completed.returncode:
        raise RuntimeError('GitHub API operation refused; check local gh authentication and repository permissions')
    return json.loads(completed.stdout)


def inspect_sources(call=api) -> list[dict]:
    lock = json.loads((ROOT/'migration/source-lock.json').read_text(encoding='utf-8'))
    if lock['canonical_repository'] != CANONICAL:
        raise ValueError('unexpected canonical repository')
    rows = []
    for source in lock['sources']:
        name = source['repository']
        if name == CANONICAL:
            continue
        if not name.startswith('SUNHAOJUN22/'):
            raise ValueError('retirement scope is restricted to the six recorded source repositories')
        metadata = call(f'repos/{name}')
        content = call(f'repos/{name}/contents/MIGRATION.json?ref=main')
        migration = json.loads(base64.b64decode(content['content']).decode('utf-8'))
        tree = call(f'repos/{name}/contents?ref=main')
        names = {item['name'] for item in tree}
        if (migration.get('canonical_repository') != CANONICAL
            or migration.get('state') != 'REDIRECT_ONLY'
            or migration.get('source_commit') != source['sha']
            or names - {'README.md','MIGRATION.json','LICENSE','LICENSE.md','NOTICE','NOTICE.md'}):
            raise ValueError('legacy main has changed or is not a verified redirect; no archive performed')
        rows.append({'repository':name,'archived':metadata.get('archived') is True,
                     'code_retired':True,'source_commit':source['sha']})
    if len(rows) != 6 or len({row['repository'] for row in rows}) != 6:
        raise ValueError('retirement set must contain exactly six unique repositories')
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',action='store_true',help='archive the six verified redirect repositories; never delete')
    parser.add_argument('--output',type=Path,default=Path('repository-retirement.json'))
    args = parser.parse_args()
    report = {'canonical_repository':CANONICAL,'requested_mode':'archive' if args.archive else 'audit',
              'repositories':[],'physical_repository_count_reduced':False,'deleted_repositories':[]}
    try:
        if not shutil.which('gh'):
            raise RuntimeError('locally authenticated GitHub CLI is required; no repository settings were changed')
        rows = inspect_sources()
        report['repositories'] = rows
        if args.archive:
            # Validate the complete scope before the first write.
            for row in rows:
                if not row['archived']:
                    api(f"repos/{row['repository']}",{'archived':True})
                row['archived'] = api(f"repos/{row['repository']}").get('archived') is True
                if not row['archived']:
                    raise RuntimeError('archive could not be confirmed by readback')
        report['state'] = 'ARCHIVED' if all(row['archived'] for row in rows) else 'REDIRECT_ONLY'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
        report['state'] = 'INCOMPLETE'
        report['error'] = str(exc)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if report['state']=='INCOMPLETE' else 0


if __name__=='__main__':
    raise SystemExit(main())
