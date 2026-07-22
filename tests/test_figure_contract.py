import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestFigure(unittest.TestCase):
    def test_example(self):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate_figure.py"),
                str(ROOT / "examples/figure-contract.json"),
            ],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
