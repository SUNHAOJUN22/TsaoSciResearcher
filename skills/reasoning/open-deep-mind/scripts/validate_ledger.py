#!/usr/bin/env python3
"""Validate an OpenDeepMind proposition-ledger JSON file without dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TYPES = {"D", "O", "L", "C", "A", "E", "V", "U"}
STATUSES = {"verified", "supported", "plausible", "contested", "unknown"}
RULES = {
    "deduction",
    "induction",
    "abduction",
    "analogy",
    "simulation",
    "optimization",
    "normative",
}
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]*$")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Iterative, deterministic DFS with an explicit graph-size budget."""
    if len(graph) > 10_000 or sum(map(len, graph.values())) > 100_000:
        raise ValueError("ledger graph exceeds the validation budget")
    cycles: list[list[str]] = []
    state = {node: 0 for node in graph}
    for root in sorted(graph):
        if state[root]:
            continue
        path: list[str] = [root]
        positions = {root: 0}
        frames = [(root, iter(sorted(graph[root])))]
        state[root] = 1
        while frames:
            node, dependencies = frames[-1]
            dep = next(dependencies, None)
            if dep is None:
                frames.pop()
                path.pop()
                positions.pop(node, None)
                state[node] = 2
            elif dep in graph and state[dep] == 0:
                state[dep] = 1
                positions[dep] = len(path)
                path.append(dep)
                frames.append((dep, iter(sorted(graph[dep]))))
            elif dep in graph and state[dep] == 1:
                cycles.append(path[positions[dep]:] + [dep])
                if len(cycles) >= 20:
                    return cycles
    return cycles


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key in ("analysis_id", "question", "domain", "scale", "purpose"):
        require(nonempty_string(data.get(key)), f"{key} must be a non-empty string", errors)
    require("claims" in data, "missing top-level field: claims", errors)

    claims = data.get("claims", [])
    require(isinstance(claims, list) and len(claims) > 0, "claims must be a non-empty list", errors)

    claim_ids: set[str] = set()
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            prefix = f"claims[{index}]"
            require(isinstance(claim, dict), f"{prefix} must be an object", errors)
            if not isinstance(claim, dict):
                continue
            for key in ("id", "type", "claim", "status", "scope", "falsifier"):
                require(key in claim, f"{prefix} missing field: {key}", errors)
            cid = claim.get("id")
            ctype = claim.get("type")
            status = claim.get("status")
            if isinstance(cid, str):
                require(bool(ID_RE.fullmatch(cid)), f"{prefix}.id is invalid: {cid}", errors)
                require(cid not in claim_ids, f"duplicate claim id: {cid}", errors)
                claim_ids.add(cid)
            else:
                errors.append(f"{prefix}.id must be a string")
            require(isinstance(ctype, str) and ctype in TYPES, f"{prefix}.type must be one of {sorted(TYPES)}", errors)
            if isinstance(cid, str) and isinstance(ctype, str) and ctype in TYPES:
                require(cid.startswith(ctype), f"{prefix}.id should start with its type {ctype}", errors)
            require(nonempty_string(claim.get("claim")), f"{prefix}.claim must be non-empty", errors)
            require(isinstance(status, str) and status in STATUSES, f"{prefix}.status must be one of {sorted(STATUSES)}", errors)
            require(isinstance(claim.get("scope"), str), f"{prefix}.scope must be a string", errors)
            require(isinstance(claim.get("falsifier"), str), f"{prefix}.falsifier must be a string", errors)
            confidence = claim.get("confidence")
            if confidence is not None:
                require(
                    isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0 <= confidence <= 1,
                    f"{prefix}.confidence must be between 0 and 1",
                    errors,
                )
            deps = claim.get("dependencies", [])
            require(isinstance(deps, list), f"{prefix}.dependencies must be a list", errors)
            if isinstance(deps, list):
                require(all(isinstance(dep, str) for dep in deps), f"{prefix}.dependencies must contain strings", errors)

    # Collect inference IDs first, so forward references can be checked consistently.
    inferences = data.get("inferences", [])
    require(isinstance(inferences, list), "inferences must be a list", errors)
    inference_ids: set[str] = set()
    if isinstance(inferences, list):
        for index, inference in enumerate(inferences):
            prefix = f"inferences[{index}]"
            require(isinstance(inference, dict), f"{prefix} must be an object", errors)
            if not isinstance(inference, dict):
                continue
            iid = inference.get("id")
            if isinstance(iid, str):
                require(bool(ID_RE.fullmatch(iid)), f"{prefix}.id is invalid: {iid}", errors)
                require(iid not in inference_ids, f"duplicate inference id: {iid}", errors)
                require(iid not in claim_ids, f"ID reused by claim and inference: {iid}", errors)
                inference_ids.add(iid)
            else:
                errors.append(f"{prefix}.id must be a string")

    all_ids = claim_ids | inference_ids
    graph: dict[str, set[str]] = {node: set() for node in all_ids}

    # Validate claim dependency references and build graph.
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
                continue
            cid = claim["id"]
            deps = claim.get("dependencies", [])
            if isinstance(deps, list):
                for dep in deps:
                    if not isinstance(dep, str):
                        continue
                    require(dep in claim_ids, f"claims[{index}] has unknown/non-claim dependency: {dep}", errors)
                    if dep in claim_ids:
                        graph[cid].add(dep)

    # Validate inference content and premise references independent of list order.
    if isinstance(inferences, list):
        for index, inference in enumerate(inferences):
            prefix = f"inferences[{index}]"
            if not isinstance(inference, dict):
                continue
            for key in ("id", "premises", "rule", "conclusion"):
                require(key in inference, f"{prefix} missing field: {key}", errors)
            iid = inference.get("id")
            premises = inference.get("premises", [])
            require(isinstance(premises, list), f"{prefix}.premises must be a list", errors)
            require(nonempty_string(inference.get("conclusion")), f"{prefix}.conclusion must be non-empty", errors)
            require(isinstance(inference.get("rule"), str) and inference.get("rule") in RULES, f"{prefix}.rule is invalid", errors)
            if isinstance(premises, list):
                require(len(premises) > 0, f"{prefix}.premises must not be empty", errors)
                for premise in premises:
                    require(isinstance(premise, str), f"{prefix}.premises must contain strings", errors)
                    if isinstance(premise, str):
                        require(premise in all_ids, f"{prefix} has unknown premise: {premise}", errors)
                        if isinstance(iid, str) and premise in all_ids:
                            graph[iid].add(premise)
            confidence = inference.get("confidence")
            if confidence is not None:
                require(
                    isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0 <= confidence <= 1,
                    f"{prefix}.confidence must be between 0 and 1",
                    errors,
                )
            defeaters = inference.get("defeaters", [])
            require(isinstance(defeaters, list), f"{prefix}.defeaters must be a list", errors)

    # The auditable reasoning graph must be acyclic.
    try:
        cycles = find_cycles(graph)
    except ValueError as exc:
        errors.append(str(exc))
        cycles = []
    for cycle in cycles:
        errors.append("dependency cycle detected: " + " -> ".join(cycle))

    decision = data.get("decision")
    if decision is not None:
        require(isinstance(decision, dict), "decision must be an object", errors)
        if isinstance(decision, dict):
            require(nonempty_string(decision.get("recommendation")), "decision.recommendation must be non-empty", errors)
            trace = decision.get("foundation_trace", [])
            require(isinstance(trace, list) and len(trace) > 0, "decision.foundation_trace must be a non-empty list", errors)
            if isinstance(trace, list):
                for item in trace:
                    require(isinstance(item, str) and item in all_ids, f"decision trace references unknown id: {item}", errors)
            if "review_trigger" in decision:
                require(nonempty_string(decision.get("review_trigger")), "decision.review_trigger must be non-empty", errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", help="path to ledger JSON")
    args = parser.parse_args()

    path = Path(args.ledger)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    if not isinstance(data, dict):
        print(json.dumps({"ok": False, "error": "top-level JSON must be an object"}))
        return 1

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "analysis_id": data.get("analysis_id"),
                "claims": len(data.get("claims", [])),
                "inferences": len(data.get("inferences", [])),
                "acyclic": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
