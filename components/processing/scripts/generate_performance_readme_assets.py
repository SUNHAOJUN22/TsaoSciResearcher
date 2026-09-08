from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_uiux_readme_assets import (  # noqa: E402
    OUT,
    render_batch_scan,
    render_perf_gate,
)

ASSETS = {
    "batch-parameter-scan.svg": render_batch_scan,
    "performance-regression-gate.svg": render_perf_gate,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in ASSETS.items():
        (OUT / name).write_text(builder(), encoding="utf-8")
    print(f"generated {len(ASSETS)} performance README assets in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
