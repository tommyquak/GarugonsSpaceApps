# Written with Super Intelligence (SI) assistance.
"""Copies the fused blocks (docs/DATA_CONTRACT.md section 6) into the app.

    python app/scripts/copy_blocks.py --blocks pipeline/out/blocks --out app/public/blocks

For each site found it writes:

    blocks_<site>.geojson    the pipeline file with coordinates rounded to 5 decimals, nothing dropped
    blocks_<site>.csv        an unchanged copy
    blocks_<site>.app.json   only when the GeoJSON is larger than --compact-over-mb: the same
                             blocks without the repeated key names, which the app loads instead

and once: ontology.json (unchanged) and index.json, the list of sites the app reads first.
The app hides its Actions view when index.json is absent.

The compact file keeps every property. Its layout:

    { "format": "blocks-compact", "version": 1, "meta": {...},
      "props": [...], "obs": [...], "states": [...],
      "rows": [ [ <one value per name in props>, [<obs values>], [<states as 1, 0 or null>],
                  [<reasons>], [x1, y1, x2, y2, ...] ], ... ] }

The last list is the outer ring of the square without its closing point.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

DECIMALS = 5
NESTED = ("obs", "states", "reasons")


def round_coords(value):
    """Rounds every number in a nested coordinate list."""
    if isinstance(value, (int, float)):
        return round(value, DECIMALS)
    return [round_coords(v) for v in value]


def dump(obj, path: Path) -> int:
    text = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return path.stat().st_size


def ordered_keys(dicts) -> list:
    keys: list = []
    for d in dicts:
        for k in d:
            if k not in keys:
                keys.append(k)
    return keys


def compact(collection: dict) -> dict | None:
    """The same blocks as rows of values. None when a feature does not fit the layout."""
    features = collection["features"]
    for f in features:
        g = f.get("geometry") or {}
        ring = (g.get("coordinates") or [[]])[0]
        plain = g.get("type") == "Polygon" and len(g["coordinates"]) == 1 and len(ring) >= 4 and ring[0] == ring[-1]
        flat = all(len(p) == 2 for p in ring)
        extra = set(f) - {"type", "properties", "geometry"}
        if not (plain and flat) or extra or not isinstance(f.get("properties"), dict):
            return None
        if any(not isinstance(f["properties"].get(k), t) for k, t in (("obs", dict), ("states", dict), ("reasons", list))):
            return None
    props = [k for k in ordered_keys(f["properties"] for f in features) if k not in NESTED]
    obs = ordered_keys(f["properties"]["obs"] for f in features)
    states = ordered_keys(f["properties"]["states"] for f in features)
    rows = []
    for f in features:
        p = f["properties"]
        flags = [None if p["states"].get(k) is None else int(bool(p["states"][k])) for k in states]
        ring = [v for point in f["geometry"]["coordinates"][0][:-1] for v in point]
        rows.append([*(p.get(k) for k in props), [p["obs"].get(k) for k in obs], flags, p["reasons"], ring])
    rest = {k: v for k, v in collection.items() if k not in ("type", "features")}
    return {"format": "blocks-compact", "version": 1, **rest, "props": props, "obs": obs, "states": states, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--blocks", required=True, type=Path, help="folder with blocks_<site>.geojson, .csv and ontology.json")
    parser.add_argument("--out", required=True, type=Path, help="folder inside the app, usually app/public/blocks")
    parser.add_argument("--compact-over-mb", type=float, default=5.0, help="write the compact file for a site whose GeoJSON is larger than this")
    args = parser.parse_args()

    ontology = args.blocks / "ontology.json"
    if not ontology.is_file():
        raise SystemExit(f"No ontology.json in {args.blocks}")
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ontology, args.out / "ontology.json")
    folder = args.out.name

    sites = []
    for source in sorted(args.blocks.glob("blocks_*.geojson")):
        match = re.fullmatch(r"blocks_(\w+)\.geojson", source.name)
        if not match:
            continue
        site = match.group(1)
        collection = json.loads(source.read_text(encoding="utf-8"))
        features = collection.get("features") or []
        if not features:
            print(f"{source.name}: no features, skipped")
            continue
        for f in features:
            f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"])
        size = dump(collection, args.out / source.name)

        lons = [p[0] for f in features for p in f["geometry"]["coordinates"][0]]
        lats = [p[1] for f in features for p in f["geometry"]["coordinates"][0]]
        counts: dict = {}
        for f in features:
            action = f["properties"].get("action")
            counts[action] = counts.get(action, 0) + 1
        entry = {
            "id": site,
            "geojson": f"{folder}/{source.name}",
            "csv": None,
            "compact": None,
            "bounds": [min(lons), min(lats), max(lons), max(lats)],
            "blocks": len(features),
            "actions": counts,
        }
        table = source.with_suffix(".csv")
        if table.is_file():
            shutil.copyfile(table, args.out / table.name)
            entry["csv"] = f"{folder}/{table.name}"
        small = args.out / f"blocks_{site}.app.json"
        small.unlink(missing_ok=True)
        note = ""
        if size > args.compact_over_mb * 1e6:
            rows = compact(collection)
            if rows is None:
                note = ", too irregular for the compact file"
            else:
                entry["compact"] = f"{folder}/{small.name}"
                note = f", compact {dump(rows, small) / 1e6:.2f} MB"
        sites.append(entry)
        print(f"{site}: {len(features)} blocks, GeoJSON {size / 1e6:.2f} MB{note}")

    if not sites:
        raise SystemExit(f"No blocks_<site>.geojson with features in {args.blocks}")
    dump({"made_by": "app/scripts/copy_blocks.py", "ontology": f"{folder}/ontology.json", "sites": sites}, args.out / "index.json")
    total = sum(p.stat().st_size for p in args.out.iterdir() if p.is_file())
    print(f"{len(sites)} sites, {total / 1e6:.2f} MB in {args.out}")


if __name__ == "__main__":
    main()
