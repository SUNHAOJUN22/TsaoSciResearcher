from __future__ import annotations
import hashlib, json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = '.tsao-research'


def load_data(path: str | Path):
    path=Path(path)
    text=path.read_text(encoding='utf-8')
    if path.suffix.lower() in {'.yaml','.yml'}:
        return yaml.safe_load(text)
    return json.loads(text)


def write_json(path: str | Path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def append_jsonl(path: str | Path, record):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(record,ensure_ascii=False)+'\n')


def read_jsonl(path: str | Path):
    path=Path(path)
    if not path.exists(): return []
    rows=[]
    for no,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as e: raise ValueError(f'{path}:{no}: invalid JSON: {e}') from e
    return rows


def sha256(path: str | Path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
