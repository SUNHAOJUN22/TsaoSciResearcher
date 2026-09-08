#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

RULES = [
    ("memory", r"out of memory|not enough memory|malloc"),
    ("disk", r"no space left|disk quota|write error"),
    ("timeout", r"time limit|walltime|cancelled.*time"),
    ("scf", r"scf.*not converged|convergence failure"),
    ("geometry", r"optimization stopped|maximum number of optimization cycles"),
    ("mpi", r"mpi_abort|segmentation fault|rank .* exited"),
    ("missing_file", r"no such file|cannot open|file not found"),
]
a = argparse.ArgumentParser()
a.add_argument("log", type=Path)
x = a.parse_args()
t = x.log.read_text(errors="replace").lower()
hits = [k for k, p in RULES if re.search(p, t, re.I)]
print(
    json.dumps(
        {"classes": hits or ["unknown"], "action": "review exact earliest error before changing inputs"}, indent=2
    )
)
