import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
from tsao_computation.project import initialize_project

p = argparse.ArgumentParser()
p.add_argument("--root", type=Path, default=Path("."))
p.add_argument("--name", required=True)
p.add_argument("--question", required=True)
a = p.parse_args()
print(initialize_project(a.root, name=a.name, question=a.question))
