"""Bounded local worker. Standard input is data, never executable code."""
from __future__ import annotations
import json
import sys
from .core.jsonio import strict_loads, strict_dumps, MAX_JSON_BYTES
from .registry import capabilities
from .adapters.local import invoke


def _plain(value):
    if isinstance(value, tuple):
        return [_plain(x) for x in value]
    if isinstance(value, list):
        return [_plain(x) for x in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def main() -> int:
    try:
        request = strict_loads(sys.stdin.buffer.read(MAX_JSON_BYTES + 1))
        cap = request["capability"]
        registry = capabilities()
        if cap not in registry or registry[cap]["mode"] != "local-reference":
            raise ValueError("capability is not locally executable")
        result = invoke(cap, request["payload"])
        text = strict_dumps({"ok": True, "result": _plain(result)})
        if len(text.encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("worker output exceeds its budget")
        sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}, allow_nan=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
