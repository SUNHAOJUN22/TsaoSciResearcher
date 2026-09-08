from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import cache

from ..registries import adapters as adapter_records
from .base import Adapter, AdapterProbe


@cache
def list_adapters() -> tuple[Adapter, ...]:
    return tuple(Adapter(record) for record in adapter_records())


@cache
def _adapter_index() -> dict[str, Adapter]:
    return {adapter.slug: adapter for adapter in list_adapters()}


def get_adapter(slug: str) -> Adapter:
    try:
        return _adapter_index()[slug]
    except KeyError as error:
        raise KeyError(f"unknown adapter: {slug}") from error


def probe_all(max_workers: int = 8) -> tuple[AdapterProbe, ...]:
    items = list_adapters()
    workers = max(1, min(max_workers, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = tuple(pool.map(lambda adapter: adapter.probe(), items))
    return tuple(sorted(results, key=lambda result: result.slug))


def clear_adapter_caches() -> None:
    _adapter_index.cache_clear()
    list_adapters.cache_clear()
