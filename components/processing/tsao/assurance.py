from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from ._utils import nonempty


class AssuranceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.out: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
        self.inc: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)

    def add_node(self, node_id: str, node_type: str, **attrs: Any) -> None:
        if not nonempty(node_id) or not nonempty(node_type):
            raise ValueError("node id and type must be non-empty")
        if node_id in self.nodes:
            raise ValueError("duplicate node")
        self.nodes[node_id] = {"type": node_type.strip(), **attrs}

    def add_edge(self, source: str, target: str, relation: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("edge endpoint missing")
        if not nonempty(relation):
            raise ValueError("edge relation must be non-empty")
        edge = (target, relation.strip())
        if edge in self.out[source]:
            raise ValueError("duplicate edge")
        self.out[source].append(edge)
        self.inc[target].append((source, relation.strip()))

    def has_path(self, source: str, target: str, relations: set[str] | None = None) -> bool:
        if source not in self.nodes or target not in self.nodes:
            return False
        queue = deque([source])
        seen = {source}
        while queue:
            node = queue.popleft()
            if node == target:
                return True
            for nxt, relation in self.out[node]:
                if relations is not None and relation not in relations:
                    continue
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return False

    def orphans(self) -> list[str]:
        return sorted(node for node in self.nodes if not self.out[node] and not self.inc[node])
