"""Derive one searchable inventory from retained source catalogs, without copying them.

Catalog records are NOT executable capabilities. Native source labels and old
validation claims do not bypass the separately validated runtime registry.
"""
from __future__ import annotations
import hashlib
import json
import yaml
from .core.jsonio import strict_loads, strict_dumps
from .workspace import root, component_registry
from .registry import capabilities


def catalog(query: str = "", owner: str | None = None) -> dict:
    if not isinstance(query, str) or len(query) > 2000:
        raise ValueError("catalog query must be a bounded string")
    components = component_registry()
    if owner is not None and owner not in components:
        raise ValueError("unknown catalog owner")
    rows = []
    seen = set()
    for component, metadata in components.items():
        folder = root()/metadata["path"]
        for spec in metadata["catalog_sources"]:
            if spec["format"] not in {"json", "yaml"}:
                raise ValueError("unsupported source catalog format")
            files = sorted(folder.glob(spec["path"]))
            if not files or len(files) > 1000:
                raise ValueError("missing or oversized source catalog")
            for path in files:
                if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or path.stat().st_size > 2*1024*1024:
                    raise ValueError("invalid catalog source path or size")
                data = path.read_bytes()
                source = strict_loads(data) if spec["format"] == "json" else yaml.safe_load(data.decode("utf-8"))
                selector = spec["selector"]
                items = [source] if selector == "@single" else source[selector] if selector else source
                if not isinstance(items, list):
                    raise ValueError("source catalog requires a list")
                for index, item in enumerate(items):
                    if isinstance(item, str):
                        native = hashlib.sha256(item.encode()).hexdigest()[:16]
                        label, level = item, "historical-description"
                        search_terms = [item]
                    elif isinstance(item, dict):
                        native = item.get("id")
                        search_terms = [item[k] for k in ("name_zh","name_cn","name_en","slug","id") if isinstance(item.get(k), str)]
                        label = next((item[k] for k in ("name_zh","name_cn","name_en","slug","id") if isinstance(item.get(k), str)), None)
                        level = next((item[k] for k in ("implementation_level","support_level","kind","activation") if isinstance(item.get(k), str)), "declared")
                    else:
                        raise ValueError("invalid source catalog entry")
                    if not isinstance(native, str) or not native or not isinstance(label, str):
                        raise ValueError("source catalog entry lacks identity or label")
                    identity = component+":"+native
                    if identity in seen:
                        raise ValueError("duplicate qualified catalog identity")
                    seen.add(identity)
                    rows.append({"id":identity,"native_id":native,"owner":component,"label":label,
                        "declared_level":level,"search_terms":search_terms,"source_file":path.relative_to(root()).as_posix(),
                        "source_sha256":hashlib.sha256(data).hexdigest(),"source_index":index,
                        "execution":"NOT_EVALUATED","native_validation_claim_reused":False})
    runtime = capabilities()
    counts = {key:sum(row['owner']==key for row in rows) for key in components}
    matched = [row for row in rows if (owner is None or row['owner']==owner)
               and (not query or query.casefold() in (row['id']+' '+' '.join(row['search_terms'])).casefold())]
    return {"schema_version":"tsao.catalog/1","total_records":len(rows),"matched_records":len(matched),
        "component_counts":counts,"runtime_local_count":sum(row['mode']=='local-reference' for row in runtime.values()),
        "entries":matched,"scope":"source metadata, not an executable capability count or scientific approval"}
