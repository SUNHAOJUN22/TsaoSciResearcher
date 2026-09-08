"""One-shot, content-bound consolidation; no source code is executed at intake."""
from __future__ import annotations
import base64, hashlib, json, lzma, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT = Path.cwd().resolve()
EXPECTED = 'f88bb22489f5c7b76922157bc84614eaa94e2d389c41e7a4286d3a1f41a2f225'
CANONICAL = 'SUNHAOJUN22/TsaoSciResearcher'
if os.environ.get('GITHUB_REPOSITORY') != CANONICAL or os.environ.get('GITHUB_REF_NAME') != 'fusion/astra-pro-1':
    raise SystemExit('Migration is restricted to the authorized repository and migration branch')

def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, timeout=300).strip()

def safe_path(relative: str) -> Path:
    path = ROOT / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or '.git' in Path(relative).parts:
        raise ValueError('Unsafe migration destination')
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError('Destination escapes the worktree')
    return path

encoded = ''.join((ROOT / f'tools/migration/part-{i}.b64').read_text().strip() for i in range(3))
compressed = base64.b64decode(encoded, validate=True)
if hashlib.sha256(compressed).hexdigest() != EXPECTED:
    raise SystemExit('Overlay checksum mismatch')
raw = lzma.decompress(compressed, memlimit=128 * 1024 * 1024)
if len(raw) > 2 * 1024 * 1024:
    raise SystemExit('Overlay size budget exceeded')
overlay = json.loads(raw)
lock = json.loads(overlay['files']['migration/source-lock.json'])
if lock['canonical_repository'] != CANONICAL or len(lock['sources']) != 7:
    raise SystemExit('Invalid seven-source inventory')
source_map = {'schema_version': 'tsao.migration/1', 'sources': []}
parents = []
with tempfile.TemporaryDirectory(prefix='tsao-migration-', dir=os.environ['RUNNER_TEMP']) as temporary:
    temporary = Path(temporary)
    for index, source in enumerate(lock['sources']):
        repository, sha, destination = source['repository'], source['sha'], source['destination']
        url = f'https://github.com/{repository}.git'
        current = git('ls-remote', '--heads', url, 'main').split()[0]
        if current != sha:
            raise SystemExit(f'Source main moved: {repository}; refusing stale consolidation')
        git('fetch', '--no-tags', url, sha)
        if git('rev-parse', f'{sha}^{{commit}}') != sha:
            raise SystemExit('Source commit identity mismatch')
        checkout = temporary / str(index)
        git('worktree', 'add', '--detach', str(checkout), sha)
        if safe_path(destination).exists():
            raise SystemExit('Refusing to overwrite an existing component')
        files = []
        for path in sorted(checkout.rglob('*')):
            if '.git' in path.relative_to(checkout).parts or not path.is_file():
                continue
            if path.is_symlink():
                raise SystemExit('Source symlink requires explicit migration review')
            relative = path.relative_to(checkout).as_posix()
            files.append({'source_path': relative, 'target_path': destination + '/' + relative,
                          'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        shutil.copytree(checkout, safe_path(destination), ignore=shutil.ignore_patterns('.git'))
        git('worktree', 'remove', str(checkout))
        source_map['sources'].append({'repository': repository, 'commit': sha,
                                     'destination': destination, 'files': files})
        if repository != CANONICAL:
            parents.append(sha)
    patch = temporary / 'source.patch'
    patch.write_text(overlay['patch'], encoding='utf-8')
    subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch)], cwd=ROOT, check=True, timeout=30)
    for name, text in overlay['files'].items():
        target = safe_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if name.startswith('.github/workflows/'):
            if not target.is_file() or target.read_text() != text:
                raise SystemExit('Root workflows must be authorized before the migration worker runs')
            continue
        target.write_text(text, encoding='utf-8')
    (ROOT / 'migration/source-map.json').write_text(json.dumps(source_map, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'components/research/LICENSE', ROOT / 'LICENSE')
    Path(os.environ['RUNNER_TEMP'], 'tsao-migration-parents.json').write_text(json.dumps(parents))
    shutil.rmtree(ROOT / 'tools/migration')
    print(json.dumps({'source_repositories': len(source_map['sources']),
                      'preserved_source_files': sum(len(x['files']) for x in source_map['sources']),
                      'additional_history_parents': len(parents),
                      'overlay_sha256': EXPECTED, 'scientific_approval': 'NOT_EVALUATED'}))
