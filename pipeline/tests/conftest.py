# Written with Super Intelligence (SI) assistance.
"""Make the pipeline folders importable in tests, the same way the scripts import each other."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("", "radar", "drying", "recovery"):
    sys.path.insert(0, str(ROOT / sub))
