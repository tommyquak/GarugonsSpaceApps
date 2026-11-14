# Written with Super Intelligence (SI) assistance.
"""Read and write pipeline/out/validation.json, the one file every reported number comes from.

Format: docs/DATA_CONTRACT.md section 3. Use put() so that entries stay consistent.
"""
import json
from pathlib import Path

PATH = Path("pipeline/out/validation.json")


def put(key, value, unit, site, made_by, status="exploratory", note=None, path=PATH):
    """Add or replace one number. Floats are rounded to 4 significant decimals."""
    data = json.loads(path.read_text()) if path.exists() else {}
    entry = {"value": round(value, 4) if isinstance(value, float) else value, "unit": unit, "site": site,
             "status": status, "made_by": made_by}
    if note:
        entry["note"] = note
    data[key] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(data.items())), indent=1) + "\n")
    return entry


def get(key, path=PATH):
    return json.loads(path.read_text())[key]
