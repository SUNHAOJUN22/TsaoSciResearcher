from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parent
REGISTRY_ROOT = PACKAGE_ROOT / "data" / "registry"
SOURCE_REGISTRY_ROOT = REPOSITORY_ROOT / "registry"
