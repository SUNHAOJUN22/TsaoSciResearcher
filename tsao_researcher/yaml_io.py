"""Strict scientific YAML input without changing ordinary merge semantics."""

from __future__ import annotations

import math
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import Any

import yaml

from .errors import ValidationError
from .io import MAX_TEXT_BYTES, read_text


class _StrictSafeLoader(yaml.SafeLoader):
    def __init__(self, stream: str) -> None:
        super().__init__(stream)
        self._checked_mappings: set[int] = set()

    def flatten_mapping(self, node: yaml.MappingNode) -> None:
        # Validate the explicit members before SafeLoader expands merge keys.
        # A legal merge may then be overridden by an explicit member. Remember
        # visited nodes so shared aliases are not rechecked after expansion.
        if id(node) not in self._checked_mappings:
            self._checked_mappings.add(id(node))
            seen: set[Hashable] = set()
            merge_marker = object()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    key = merge_marker
                elif key_node.tag == "tag:yaml.org,2002:value":
                    key = key_node.value
                else:
                    key = self.construct_object(key_node)
                if not isinstance(key, Hashable):
                    raise ValidationError("YAML mapping key must be hashable")
                if key in seen:
                    raise ValidationError(f"duplicate YAML key is forbidden: {key!r}")
                seen.add(key)
        super().flatten_mapping(node)

    def construct_strict_float(self, node: yaml.ScalarNode) -> float:
        result = super().construct_yaml_float(node)
        if not math.isfinite(result):
            raise ValidationError("non-finite YAML number is forbidden")
        significand = node.value.lower().split("e", 1)[0]
        if result == 0.0 and any(digit in "123456789" for digit in significand):
            raise ValidationError("non-zero YAML number underflows the finite numeric range")
        return result


_StrictSafeLoader.add_constructor("tag:yaml.org,2002:float", _StrictSafeLoader.construct_strict_float)


def decode_yaml(text: str) -> Any:
    loader = _StrictSafeLoader(text)
    try:
        return loader.get_single_data()
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML document: {exc}") from exc
    finally:
        dispose: Callable[[], None] = loader.dispose
        dispose()


def load_yaml(path: str | Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Any:
    return decode_yaml(read_text(path, max_bytes=max_bytes))
