# Written with Super Intelligence (SI) assistance.
"""Fuse the layers into one record per 1 km block: observations, states, an action and its reasons.

The vocabulary, the thresholds and the decision table live in ontology.json next to this
file. Nothing is weighted or learned: a state needs independent sources to agree, and an
action is the first rule in the table that a block's states satisfy. Each block keeps the
numbers that decided it, so every recommendation can explain itself.

Writes, for one site (docs/DATA_CONTRACT.md section 6):

  blocks_<site>.geojson   1 km squares in lon/lat with their observations, states, action,
                          confidence, rank and reasons
  blocks_<site>.csv       the same table without geometry, for a spreadsheet or a GPS
  ontology.json           a copy of the vocabulary, for the app

    python pipeline/fusion/blocks.py --site west --tracks 125 061 --dry-until 20261025 \\
        --stacks pipeline/out/stacks --layers pipeline/out/layers --out pipeline/out/blocks
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
from common import block_mean, load_stack  # noqa: E402
from drydown import normalised  # noqa: E402
from vjson import get, put  # noqa: E402

ME = "pipeline/fusion/blocks.py"
ONTOLOGY_FILE = Path(__file__).parent / "ontology.json"
SIDE = 20            # 20 pixels of 50 m make a 1 km block
MIN_VALID = 0.5      # a block needs radar data over at least half of it


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.crs.to_epsg()


def per_block(a, how):
    """Aggregate a 50 m layer over SIDE by SIDE blocks, ignoring NaN."""
    rows, cols = (a.shape[0] // SIDE) * SIDE, (a.shape[1] // SIDE) * SIDE
    cube = a[:rows, :cols].reshape(rows // SIDE, SIDE, cols // SIDE, SIDE).swapaxes(1, 2).reshape(rows // SIDE, cols // SIDE, SIDE * SIDE)
    with np.errstate(all="ignore"):
        return {"median": np.nanmedian, "mean": np.nanmean, "max": np.nanmax}[how](cube, axis=2)


def hv_left(stack, baseline, dry_until):
    """HV on the first pass after the rain minus HV at the start of the season, on 250 m blocks."""
    layers = normalised(stack, baseline, "hv")
    wet = [i for i, d in enumerate(stack["dates"]) if d > dry_until]
    if not wet:
        return None, None
    start = np.mean([block_mean(layers[0]), block_mean(layers[1])], axis=0)
    return block_mean(layers[wet[0]]) - start, stack["dates"][wet[0]]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--tracks", nargs=2, required=True, metavar=("ASCENDING", "DESCENDING"))
    p.add_argument("--dry-until", required=True)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    onto = json.loads(ONTOLOGY_FILE.read_text())
    th = onto["thresholds"]
    asc, desc = a.tracks
    L = a.layers

    # ---- observations, each as one value per block. Falls and "left" are positive when the echo is lower.
    drop_a, T, epsg = read(L / f"drydown_{a.site}_{asc}.tif")
    drop_d, _, _ = read(L / f"drydown_{a.site}_{desc}.tif")
    valid = per_block((np.isfinite(drop_a) & np.isfinite(drop_d)).astype("float32"), "mean")
    obs = {"fall_asc": -per_block(drop_a, "median"), "fall_desc": -per_block(drop_d, "median")}
    after = {}
    for key, track in (("asc", asc), ("desc", desc)):
        stack = load_stack(a.stacks / f"{a.site}_{track}.npz")
        base = json.loads((L / f"baseline_{track}.json").read_text())
        wet = [d for d in stack["dates"] if d > a.dry_until]
        if wet:
            after[key] = wet[0]
            obs[f"left_{key}"] = -per_block(read(L / f"hh_{a.site}_{track}_{wet[0]}.tif")[0], "median")
            obs[f"hv_left_{key}"] = -per_block(hv_left(stack, base, a.dry_until)[0], "median")
        else:
            obs[f"left_{key}"] = obs[f"hv_left_{key}"] = np.full(valid.shape, np.nan)
    fire = read(L / f"fire_days_{a.site}.tif")[0]
    obs["fire_share"] = per_block((fire > 0).astype("float32"), "mean")
    obs["fire_days"] = per_block(fire, "max")
    obs["peat_share"] = per_block(read(L / f"peat_peatmap_{a.site}.tif")[0], "mean")
    obs["canal_m"] = per_block(read(L / f"canal_distance_{a.site}.tif")[0], "median")
    floor = {"asc": abs(get(f"noise_floor_hh_{asc}")["value"]), "desc": abs(get(f"noise_floor_hh_{desc}")["value"])}

    # ---- states: the decision table of ontology.json, written out
    with np.errstate(invalid="ignore"):
        st = {
            "on_peat": obs["peat_share"] >= th["peat_share"],
            "dried": (obs["fall_asc"] >= th["fall_db"]) & (obs["fall_desc"] >= th["fall_db"]),
            "burnt": obs["fire_share"] >= th["burnt_share"],
            "not_back": (obs["left_asc"] > floor["asc"]) & (obs["left_desc"] > floor["desc"]),
            "drained": obs["canal_m"] <= th["canal_m"],
        }
        st["canopy_lost"] = st["burnt"] & (obs["hv_left_asc"] >= th["hv_left_db"]) & (obs["hv_left_desc"] >= th["hv_left_db"])
        extra = {"persistent_fire": obs["fire_days"] >= th["persistent_fire_days"],
                 "strong_fall": (obs["fall_asc"] >= 2 * th["fall_db"]) & (obs["fall_desc"] >= 2 * th["fall_db"])}

    # ---- actions: first rule that holds
    action = np.full(valid.shape, "none", dtype=object)
    action[st["on_peat"] & st["dried"] & ~st["burnt"] & ~st["not_back"]] = "watch"
    action[st["on_peat"] & st["dried"] & ~st["burnt"] & st["not_back"]] = "rewet_first"
    action[st["on_peat"] & st["burnt"]] = "assess_burn"
    stronger = {x["id"]: x["stronger_if"] for x in onto["actions"]}
    flags = {**st, **extra}
    points = np.ones(valid.shape, int)
    for name, conditions in stronger.items():
        for c in conditions:
            points += ((action == name) & flags[c]).astype(int)
    confidence = np.where(points >= 3, "high", np.where(points == 2, "medium", "low"))
    confidence[action == "none"] = ""
    fall = (obs["fall_asc"] + obs["fall_desc"]) / 2

    # ---- one record per block
    keep = valid >= MIN_VALID
    to_lonlat = Transformer.from_crs(epsg, 4326, always_xy=True)
    order = {}   # rank inside each action, largest fall first
    for name in ("assess_burn", "rewet_first", "watch"):
        idx = np.argwhere(keep & (action == name))
        for rank, (r, c) in enumerate(sorted(idx, key=lambda rc: -fall[rc[0], rc[1]]), start=1):
            order[(int(r), int(c))] = rank

    def num(v, digits=2):
        return None if not np.isfinite(v) else round(float(v), digits)

    features, table = [], []
    for r, c in np.argwhere(keep):
        r, c = int(r), int(c)
        o = {k: num(v[r, c], 0 if k in ("fire_days", "canal_m") else 2) for k, v in obs.items()}
        s = {k: bool(v[r, c]) for k, v in st.items()}
        act = str(action[r, c])
        corners = [T * (c * SIDE + dc * SIDE, r * SIDE + dr * SIDE) for dc, dr in ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))]
        ring = [[round(v, 5) for v in to_lonlat.transform(x, y)] for x, y in corners]
        lon, lat = (round(v, 5) for v in to_lonlat.transform(*(T * (c * SIDE + SIDE / 2, r * SIDE + SIDE / 2))))
        reasons = [f"{o['peat_share']:.0%} of the block is on mapped peat." if o["peat_share"] is not None else "Peat cover unknown."]
        if o["fall_asc"] is not None:
            verb = "fell" if (o["fall_asc"] + o["fall_desc"]) > 0 else "rose"
            reasons.append(f"HH {verb} {abs(o['fall_asc']):.1f} dB on the dawn orbit and {abs(o['fall_desc']):.1f} dB on the dusk orbit over the dry season.")
        reasons.append(f"Fire was detected within 200 m of {o['fire_share']:.0%} of the block, on up to {int(o['fire_days'])} days." if o["fire_share"] else "No fire was detected within 200 m.")
        if o["left_asc"] is not None and o["left_desc"] is not None and s["dried"]:
            reasons.append(f"After the rain HH is still {max(o['left_asc'], 0):.1f} and {max(o['left_desc'], 0):.1f} dB below the start of the season (noise floor {floor['asc']:.1f} and {floor['desc']:.1f})." if s["not_back"]
                           else "After the rain HH came back to within the noise floor on at least one orbit.")
        if s["canopy_lost"]:
            reasons.append(f"HV, the canopy signal, is still {o['hv_left_asc']:.1f} and {o['hv_left_desc']:.1f} dB down after the rain.")
        if o["canal_m"] is not None:
            reasons.append(f"Typical distance to a mapped canal: {int(o['canal_m'])} m.")
        props = {"id": f"{a.site}-{r:03d}-{c:03d}", "site": a.site, "lon": lon, "lat": lat, "action": act,
                 "confidence": str(confidence[r, c]) or None, "rank": order.get((r, c)), "fall_db": num(fall[r, c]),
                 "obs": o, "states": s, "reasons": reasons}
        features.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring]}})
        table.append({"id": props["id"], "action": act, "confidence": props["confidence"] or "", "rank": props["rank"] or "", "lon": lon, "lat": lat,
                      "fall_db": props["fall_db"], **o, **{f"is_{k}": int(v) for k, v in s.items()}})

    a.out.mkdir(parents=True, exist_ok=True)
    meta = {"site": a.site, "block_m": SIDE * 50, "tracks": {"asc": asc, "desc": desc}, "pass_after_rain": after, "dry_until": a.dry_until,
            "noise_floor_db": floor, "caveat": onto["caveat"],
            "sources": "NISAR L2 GCOV (NASA, ISRO); FIRMS (NASA); PEATMAP, Xu et al. 2018, CC BY 4.0; OpenStreetMap contributors"}
    (a.out / f"blocks_{a.site}.geojson").write_text(json.dumps({"type": "FeatureCollection", "meta": meta, "features": features}, separators=(",", ":")) + "\n")
    with open(a.out / f"blocks_{a.site}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    shutil.copyfile(ONTOLOGY_FILE, a.out / "ontology.json")

    line = []
    for name in ("assess_burn", "rewet_first", "watch", "none"):
        n = int((keep & (action == name)).sum())
        put(f"blocks_{name}_{a.site}", n, "blocks of 1 km", a.site, ME, note=next(x["rule"] for x in onto["actions"] if x["id"] == name))
        line.append(f"{name} {n}")
    for level in ("high", "medium", "low"):
        put(f"blocks_rewet_first_{level}_{a.site}", int((keep & (action == "rewet_first") & (confidence == level)).sum()), "blocks of 1 km", a.site, ME)
    print(f"{a.site}: {len(features)} blocks; " + ", ".join(line) + f"; rewet_first by confidence: " +
          ", ".join(f"{lv} {int((keep & (action == 'rewet_first') & (confidence == lv)).sum())}" for lv in ("high", "medium", "low")))


if __name__ == "__main__":
    main()
