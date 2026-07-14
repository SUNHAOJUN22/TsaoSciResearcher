#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.md', '.py', '.json', '.yaml', '.yml', '.toml', '.txt', '.csv', '.ps1', '.sh'}
REQUIRED_WORKFLOWS = {
    'research-question', 'deep-research', 'systematic-review', 'research-design',
    'experiment-design', 'data-analysis', 'scientific-figure', 'scientific-writing',
    'peer-review', 'technical-report', 'project-management', 'patent-and-transfer',
    'research-integrity', 'laboratory', 'computation-handoff'
}
REQUIRED_SCHEMAS = {
    'research-project.schema.json', 'evidence-record.schema.json', 'claim.schema.json',
    'figure-contract.schema.json', 'experiment-protocol.schema.json',
    'artifact-manifest.schema.json', 'computation-handoff.schema.json'
}
REQUIRED_SCRIPTS = {
    'init_project.py', 'route_task.py', 'validate_project.py', 'validate_evidence.py',
    'validate_citations.py', 'validate_claims.py', 'validate_figure.py',
    'validate_export.py', 'build_capability_index.py', 'validate_structure.py',
    'handoff_to_computation.py', 'install.py', 'package_release.py', 'generate_checksums.py', 'run_tests.py'
}


def markdown_local_links(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    links = []
    for href in re.findall(r'(?:\[[^\]]*\]\(|href=["\']|src=["\'])([^)"\']+)', text):
        href = href.strip()
        if not href or href.startswith(('#', 'mailto:', 'data:')) or '://' in href:
            continue
        links.append(href.split('#', 1)[0])
    return links


def load_capabilities() -> tuple[dict, list[dict]]:
    index_path = ROOT / 'capability-index' / 'capabilities.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    rows: list[dict] = []
    for shard in index['shards']:
        shard_path = ROOT / shard['path']
        payload = json.loads(shard_path.read_text(encoding='utf-8'))
        rows.extend(payload['capabilities'])
    return index, rows


def audit() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, object] = {}

    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    skill_text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    agent = yaml.safe_load((ROOT / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
    pyproject = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    versions = {
        'VERSION': version,
        'manifest': str(manifest.get('version')),
        'SKILL': (re.search(r'^version:\s*["\']?([^\s"\']+)', skill_text, re.M) or [None, None])[1],
        'agent': str(agent.get('version')),
        'pyproject': (re.search(r'^version\s*=\s*["\']([^"\']+)', pyproject, re.M) or [None, None])[1],
    }
    if len(set(versions.values())) != 1:
        errors.append(f'version mismatch: {versions}')
    checks['versions'] = versions

    workflow_dirs = {p.parent.name for p in (ROOT / 'workflows').glob('*/WORKFLOW.md')}
    missing_workflows = sorted(REQUIRED_WORKFLOWS - workflow_dirs)
    if missing_workflows:
        errors.append(f'missing workflows: {missing_workflows}')
    checks['workflows'] = {'count': len(workflow_dirs), 'missing': missing_workflows}

    schema_names = {p.name for p in (ROOT / 'schemas').glob('*.json')}
    missing_schemas = sorted(REQUIRED_SCHEMAS - schema_names)
    if missing_schemas:
        errors.append(f'missing schemas: {missing_schemas}')
    checks['schemas'] = {'count': len(schema_names), 'missing': missing_schemas}

    script_names = {p.name for p in (ROOT / 'scripts').glob('*.py')}
    missing_scripts = sorted(REQUIRED_SCRIPTS - script_names)
    if missing_scripts:
        errors.append(f'missing scripts: {missing_scripts}')
    checks['scripts'] = {'count': len(script_names), 'missing': missing_scripts}

    index, capabilities = load_capabilities()
    required_fields = {
        'id', 'slug', 'name_zh', 'name_en', 'category_zh', 'description_zh',
        'workflow', 'triggers', 'inputs', 'outputs', 'recommended_tools', 'risk_level',
        'human_approval_required', 'tsao_sci_computation_handoff', 'references'
    }
    slugs = []
    for row_no, cap in enumerate(capabilities, start=1):
        missing = required_fields - set(cap)
        if missing:
            errors.append(f'capability {row_no} missing fields: {sorted(missing)}')
        slugs.append(cap.get('slug'))
        workflow = cap.get('workflow')
        if workflow not in workflow_dirs:
            errors.append(f'capability {cap.get("slug")} references missing workflow {workflow}')
        for rel in cap.get('references', []):
            if not (ROOT / rel).exists():
                errors.append(f'capability {cap.get("slug")} references missing file {rel}')
    if len(capabilities) != 158 or index.get('total') != 158:
        errors.append(f'capability total is {len(capabilities)} / declared {index.get("total")}, expected 158')
    if len(slugs) != len(set(slugs)):
        errors.append('duplicate capability slugs')
    checks['capabilities'] = {'loaded': len(capabilities), 'declared': index.get('total'), 'unique_slugs': len(set(slugs))}

    router = json.loads((ROOT / 'router_rules.json').read_text(encoding='utf-8'))
    missing_router = sorted(REQUIRED_WORKFLOWS - set(router))
    if missing_router:
        errors.append(f'router missing workflows: {missing_router}')
    for workflow in REQUIRED_WORKFLOWS:
        expected = f'workflows/{workflow}/WORKFLOW.md'
        if expected not in skill_text:
            errors.append(f'SKILL.md does not route to {expected}')
    checks['router'] = {'rules': len(router), 'missing': missing_router}

    checked_links = 0
    for md in [ROOT / 'README.md', ROOT / 'README.zh-CN.md', ROOT / 'README_EN.md']:
        for rel in markdown_local_links(md):
            checked_links += 1
            if not (ROOT / rel).exists():
                errors.append(f'broken local link in {md.name}: {rel}')
    checks['readme_links'] = checked_links

    ci_text = (ROOT / '.github' / 'workflows' / 'ci.yml').read_text(encoding='utf-8')
    for rel in ['requirements-dev.txt', 'scripts/run_tests.py']:
        if rel not in ci_text:
            errors.append(f'CI does not reference {rel}')
        if not (ROOT / rel).exists():
            errors.append(f'CI target missing: {rel}')

    contaminated = [str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if '__pycache__' in p.parts or p.suffix in {'.pyc', '.pyo'}]
    if contaminated:
        errors.append(f'generated bytecode committed: {contaminated[:10]}')
    checks['bytecode_contamination'] = len(contaminated)

    forbidden = [p for p in ROOT.rglob('*') if p.is_file() and p.name.lower() in {'.env', 'credentials.json', 'secrets.json'}]
    if forbidden:
        errors.append(f'credential-like files present: {[str(p.relative_to(ROOT)) for p in forbidden]}')

    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        if re.search(r'sk-[A-Za-z0-9]{20,}', text):
            errors.append(f'possible API key in {path.relative_to(ROOT)}')

    checks['files'] = sum(1 for p in ROOT.rglob('*') if p.is_file())
    checks['status'] = 'PASS' if not errors else 'FAIL'
    return {'status': checks['status'], 'checks': checks, 'errors': errors, 'warnings': warnings}


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit the complete TsaoSciResearcher repository.')
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = parser.parse_args()
    result = audit()
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"repository audit {result['status']}")
        for key, value in result['checks'].items():
            print(f'- {key}: {value}')
        for warning in result['warnings']:
            print(f'WARNING: {warning}')
        for error in result['errors']:
            print(f'ERROR: {error}', file=sys.stderr)
    if result['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
