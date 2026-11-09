#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import read_jsonl

DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
URL = re.compile(r"^https?://", re.I)


def recognized_paper_locator(locator: str) -> bool:
    """Check *format* only; no network resolution or source authenticity claim."""
    if DOI.fullmatch(locator):
        return True
    if URL.match(locator):
        try:
            parsed = urlsplit(locator)
            return (
                bool(parsed.hostname and parsed.hostname.strip("."))
                and not any(character.isspace() for character in locator)
                and parsed.username is None
                and parsed.password is None
            )
        except ValueError:
            return False
    lower = locator.lower()
    return any(
        lower.startswith(prefix) and bool(locator[len(prefix) :].strip())
        for prefix in ("pmid:", "arxiv:", "isbn:")
    )



def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence_jsonl")
    a = p.parse_args()
    try:
        warnings = []
        for r in read_jsonl(a.evidence_jsonl):
            if r["source"]["kind"] == "paper":
                loc = r["source"]["locator"].strip()
                if not recognized_paper_locator(loc):
                    warnings.append(
                        f"{r['evidence_id']}: paper locator is not a recognized DOI/URL/identifier"
                    )
        print(f"citation format check PASS warnings={len(warnings)}")
        for w in warnings:
            print("WARNING", w)
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
