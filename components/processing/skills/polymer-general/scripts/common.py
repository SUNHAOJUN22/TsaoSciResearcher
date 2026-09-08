from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


def load_structured(path: str | Path) -> Any:
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig")
    if source.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def dump_json(path: str | Path, obj: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: str | Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def slugify(value: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", value.strip(), flags=re.UNICODE).strip("-")
    return slug or "project"
