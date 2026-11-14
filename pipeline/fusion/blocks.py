# Written with Super Intelligence (SI) assistance.
"""Fuse the layers into one record per 1 km block: observations, states, a screening class and its reasons.

The vocabulary, the thresholds and the decision table live in ontology.json next to this
file. Nothing is weighted or learned: a state is a fixed rule over observations, and a class
is the first rule in the table that a block's states satisfy. Each block keeps the numbers
that decided it, so every class can show its working. A class says what was seen and what a
field team could check. It is not a recommendation to intervene.

Writes, for one site (docs/DATA_CONTRACT.md section 6):

  blocks_<site>.geojson   1 km squares in lon/lat with their observations, states, action,
                          confidence, rank and reasons
  blocks_<site>.csv       the same table without geometry, for a spreadsheet or a GPS
  ontology.json           a copy of the vocabulary, for the app

    python pipeline/fusion/blocks.py --site west --tracks 125 061 --start-from 20260710 --dry-until 20261025 \\
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
from scipy.ndimage import binary_dilation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
from common import block_mean, load_stack  # noqa: E402
from drydown import normalised  # noqa: E402
from season import start_passes  # noqa: E402
from vjson import put  # noqa: E402

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


def hv_left(stack, dry_until, start_from):
    """HV on the first pass after the rain minus HV on the start passes, on 250 m blocks.

    HV is used as measured, without the forest baseline: in the reference forest HV rises by
    about half a decibel over the season, and subtracting that rise would make every other
    kind of land look as if it had lost that much."""
    layers = stack["hv"]
    wet = [i for i, d in enumerate(stack["dates"]) if d > dry_until]
    if not wet:
        return None, None
    start = np.mean([block_mean(layers[i]) for i in start_passes(stack["dates"], start_from)], axis=0)
    return block_mean(layers[wet[0]]) - start, stack["dates"][wet[0]]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--tracks", nargs=2, required=True, metavar=("ASCENDING", "DESCENDING"))
    p.add_argument("--start-from", help="YYYYMMDD, earliest day for a start pass (pipeline/season.py)")
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
        wet = [d for d in stack["dates"] if d > a.dry_until]
        if wet:
            after[key] = wet[0]
            obs[f"left_{key}"] = -per_block(read(L / f"hh_{a.site}_{track}_{wet[0]}.tif")[0], "median")
            obs[f"hv_left_{key}"] = -per_block(hv_left(stack, a.dry_until, a.start_from)[0], "median")
        else:
            obs[f"left_{key}"] = obs[f"hv_left_{key}"] = np.full(valid.shape, np.nan)
    fire = read(L / f"fire_days_{a.site}.tif")[0]
    obs["fire_share"] = per_block((fire > 0).astype("float32"), "mean")
    obs["fire_days"] = per_block(fire, "max")
    obs["fire_share_1km"] = per_block((read(L / f"fire_days_1km_{a.site}.tif")[0] > 0).astype("float32"), "mean")
    obs["peat_share"] = per_block(read(L / f"peat_peatmap_{a.site}.tif")[0], "mean")
    obs["canal_m"] = per_block(read(L / f"canal_distance_{a.site}.tif")[0], "median")

    # ---- states: the decision table of ontology.json, written out
    with np.errstate(invalid="ignore"):
        st = {
            "on_peat": obs["peat_share"] >= th["peat_share"],
            "fell": (obs["fall_asc"] >= th["fall_db"]) & (obs["fall_desc"] >= th["fall_db"]),
            "fire": obs["fire_share"] >= th["burnt_share"],
            "still_low": (obs["left_asc"] >= th["left_db"]) & (obs["left_desc"] >= th["left_db"]),
            "persistent_fire": obs["fire_days"] >= th["persistent_fire_days"],
            "clear_of_fire": obs["fire_share_1km"] == 0,
            "near_canal": obs["canal_m"] <= th["canal_m"],
        }
        st["canopy_low"] = st["fire"] & (obs["hv_left_asc"] >= th["hv_left_db"]) & (obs["hv_left_desc"] >= th["hv_left_db"])

    # ---- classes: first rule that holds
    action = np.full(valid.shape, "none", dtype=object)
    action[st["on_peat"] & st["fell"] & ~st["fire"] & ~st["still_low"]] = "fell_came_back"
    action[st["on_peat"] & st["fell"] & ~st["fire"] & st["still_low"]] = "fell_still_low"
    action[st["on_peat"] & st["fire"]] = "fire_detected"
    stronger = {x["id"]: x["stronger_if"] for x in onto["actions"]}
    points = np.ones(valid.shape, int)
    for name, conditions in stronger.items():
        for c in conditions:
            points += ((action == name) & st[c]).astype(int)
    confidence = np.where(points >= 3, "high", np.where(points == 2, "medium", "low"))
    confidence[action == "none"] = ""
    fall = (obs["fall_asc"] + obs["fall_desc"]) / 2
    CLASSES = ("fire_detected", "fell_still_low", "fell_came_back")

    # ---- one record per block
    keep = valid >= MIN_VALID
    to_lonlat = Transformer.from_crs(epsg, 4326, always_xy=True)
    order = {}   # rank inside each action, largest fall first
    for name in CLASSES:
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
            reasons.append(f"HH {verb} {abs(o['fall_asc']):.1f} dB on the dawn orbit and {abs(o['fall_desc']):.1f} dB on the dusk orbit between the dry start in July and mid October.")
        if o["fire_share"]:
            reasons.append(f"{o['fire_share']:.0%} of the block lies inside the footprint of a fire detection, on up to {int(o['fire_days'])} days.")
        elif o["fire_share_1km"]:
            reasons.append(f"No fire detection reaches the block, but {o['fire_share_1km']:.0%} of it is within 1 km of one.")
        else:
            reasons.append("No fire was detected within 1 km.")
        if o["left_asc"] is not None and o["left_desc"] is not None and s["fell"]:
            reasons.append(f"On the first pass after the rain HH was {o['left_asc']:+.1f} and {o['left_desc']:+.1f} dB from the dry start (positive is still lower), one pass per orbit.".replace("+-", "-"))
        if s["canopy_low"]:
            reasons.append(f"HV was still {o['hv_left_asc']:.1f} and {o['hv_left_desc']:.1f} dB below the dry start after the rain.")
        if o["canal_m"] is not None:
            reasons.append(f"Typical distance to a mapped canal: {int(o['canal_m'])} m.")
        props = {"id": f"{a.site}-{r:03d}-{c:03d}", "site": a.site, "lon": lon, "lat": lat, "action": act,
                 "confidence": str(confidence[r, c]) or None, "rank": order.get((r, c)), "fall_db": num(fall[r, c]),
                 "obs": o, "states": s, "reasons": reasons}
        features.append({"type": "Feature", "properties": props, "geometry": {"type": "Polygon", "coordinates": [ring]}})
        table.append({"id": props["id"], "action": act, "confidence": props["confidence"] or "", "rank": props["rank"] or "", "lon": lon, "lat": lat,
                      "fall_db": props["fall_db"], **o, **{f"is_{k}": int(v) for k, v in s.items()}})

    a.out.mkdir(parents=True, exist_ok=True)
    meta = {"site": a.site, "block_m": SIDE * 50, "tracks": {"asc": asc, "desc": desc}, "pass_after_rain": after,
            "start_from": a.start_from, "dry_until": a.dry_until, "ontology_version": onto["version"], "caveat": onto["caveat"],
            "sources": "NISAR L2 GCOV (NASA, ISRO); FIRMS (NASA); PEATMAP, Xu et al. 2018, CC BY 4.0; OpenStreetMap contributors"}
    (a.out / f"blocks_{a.site}.geojson").write_text(json.dumps({"type": "FeatureCollection", "meta": meta, "features": features}, separators=(",", ":")) + "\n")
    with open(a.out / f"blocks_{a.site}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    shutil.copyfile(ONTOLOGY_FILE, a.out / "ontology.json")

    line = []
    for name in CLASSES + ("none",):
        n = int((keep & (action == name)).sum())
        put(f"blocks_{name}_{a.site}", n, "blocks of 1 km", a.site, ME, note=next(x["rule"] for x in onto["actions"] if x["id"] == name))
        line.append(f"{name} {n}")
    clear = int((keep & (action == "fell_still_low") & st["clear_of_fire"]).sum())
    put(f"blocks_fell_still_low_clear_of_fire_{a.site}", clear, "blocks of 1 km", a.site, ME, note="with no fire detection within 1 km")
    print(f"{a.site}: {len(features)} blocks; " + ", ".join(line) + f"; fell_still_low with no fire within 1 km: {clear}")


if __name__ == "__main__":
    main()
