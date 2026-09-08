from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, NoReturn, SupportsIndex


class FrozenDict(dict[str, Any]):
    """JSON-compatible dictionary that rejects in-place mutation."""

    __slots__ = ()

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("immutable mapping cannot be modified")

    def __setitem__(self, key: str, value: Any) -> NoReturn:
        self._immutable()

    def __delitem__(self, key: str) -> NoReturn:
        self._immutable()

    def clear(self) -> NoReturn:
        self._immutable()

    def pop(self, key: str, default: Any = None) -> NoReturn:
        self._immutable()

    def popitem(self) -> NoReturn:
        self._immutable()

    def setdefault(self, key: str, default: Any = None) -> NoReturn:
        self._immutable()

    def update(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._immutable()

    def __ior__(self, value: Any) -> FrozenDict:  # type: ignore[override,misc]
        self._immutable()

    def __copy__(self) -> FrozenDict:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenDict:
        return self


class FrozenList(list[Any]):
    """JSON-compatible list that rejects in-place mutation."""

    __slots__ = ()

    @staticmethod
    def _immutable() -> NoReturn:
        raise TypeError("immutable sequence cannot be modified")

    def __setitem__(self, key: Any, value: Any) -> NoReturn:
        self._immutable()

    def __delitem__(self, key: Any) -> NoReturn:
        self._immutable()

    def __iadd__(self, value: Iterable[Any]) -> FrozenList:  # type: ignore[misc]
        self._immutable()

    def __imul__(self, value: SupportsIndex) -> FrozenList:
        self._immutable()

    def append(self, value: Any) -> NoReturn:
        self._immutable()

    def clear(self) -> NoReturn:
        self._immutable()

    def extend(self, values: Any) -> NoReturn:
        self._immutable()

    def insert(self, index: SupportsIndex, value: Any) -> NoReturn:
        self._immutable()

    def pop(self, index: SupportsIndex = -1) -> NoReturn:
        self._immutable()

    def remove(self, value: Any) -> NoReturn:
        self._immutable()

    def reverse(self) -> NoReturn:
        self._immutable()

    def sort(self, *args: Any, **kwargs: Any) -> NoReturn:
        self._immutable()

    def __copy__(self) -> FrozenList:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenList:
        return self


def freeze_json(value: Any) -> Any:
    if isinstance(value, (FrozenDict, FrozenList)):
        return value
    if isinstance(value, Mapping):
        return FrozenDict({str(key): freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return FrozenList(freeze_json(item) for item in value)
    if isinstance(value, tuple):
        return tuple(freeze_json(item) for item in value)
    return value


def thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw_json(item) for item in value]
    return value
