# Written with Super Intelligence (SI) assistance.
"""A hindcast: did the radar show, part way through the dry season, which peat was ready to burn?

This is not a forecast. Fires here are lit by people, and the radar cannot see intent. What
it can see is the condition of the ground. The test is done after the fact on this one
season: take the 1 km peat blocks with no fire before a cut date, split them by how far HH
had already fallen on the last pass of each orbit before that date, and count how many had
fire afterwards. If drying marks fire-prone ground, the burn rate should climb with the fall.

"Early fall" means HH had fallen by --early-db or more on both orbits by the cut date,
measured from the dry start passes (so the cut must come after them: the default is
1 September). "Burned later" means fire detections on --min-days or more separate days
inside the block from the cut date on.

Blocks next to each other are not independent, so every difference comes with a 95% range
from resampling whole 10 km tiles. Read the range before the number.

Writes hindcast_<site>.json (per block: id, early fall, early dry, burned later, for the
app's replay) and numbers in validation.json, including how well distance to a canal does
on its own, so the result can be judged against the simplest alternative.

    python pipeline/fusion/hindcast.py --site west --tracks 125 061 --cut 2026-09-01 \\
        --layers pipeline/out/layers --firms data/firms/west --out pipeline/out/blocks
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from blocks import SIDE, per_block  # noqa: E402
from vjson import put  # noqa: E402

ME = "pipeline/fusion/hindcast.py"
MODIS_MIN_CONFIDENCE = 30


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.crs.to_epsg()


def auc(score, outcome):
    """Chance that a random block that burned scores higher than one that did not. 0.5 is no skill."""
    k = np.isfinite(score)
    score, outcome = score[k], outcome[k]
    ranks = score.argsort().argsort() + 1.0
    n1, n0 = outcome.sum(), (~outcome).sum()
    return float((ranks[outcome].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")


def tile_interval(early, burned, rows, cols, tile=10, draws=400, seed=1):
    """95% range of (burn rate if early fall) minus (burn rate if not), resampling whole tiles of `tile` blocks."""
    tiles = (rows // tile) * 10000 + (cols // tile)
    ids = np.unique(tiles)
    members = [np.where(tiles == t)[0] for t in ids]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        pick = np.concatenate([members[i] for i in rng.integers(0, len(ids), len(ids))])
        e, b = early[pick], burned[pick]
        if e.any() and (~e).any():
            out.append(b[e].mean() - b[~e].mean())
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float(lo), float(hi), len(ids)


def last_pass_before(layers, site, track, cut):
    """The per-pass layer of the last pass before the cut date."""
    files = sorted(layers.glob(f"hh_{site}_{track}_*.tif"))
    before = [f for f in files if f.stem.split("_")[-1] < cut.replace("-", "")]
    if len(before) < 2:
        raise SystemExit(f"track {track} has fewer than two passes before {cut}")
    return before[-1]


def fire_days_by_block(firms, T, epsg, shape, cut):
    """Days with a kept detection in each block, before the cut and from the cut on."""
    to_grid = Transformer.from_crs(4326, epsg, always_xy=True)
    before, after, seen = np.zeros(shape, int), np.zeros(shape, int), set()
    for f in sorted(Path(firms).glob("firms_*.csv")):
        with open(f, newline="") as fh:
            for row in csv.DictReader(fh):
                c = row.get("confidence", "").strip().lower()
                if c in ("l", "low") or (c.isdigit() and int(c) < MODIS_MIN_CONFIDENCE):
                    continue
                x, y = to_grid.transform(float(row["longitude"]), float(row["latitude"]))
                col, r = ~T * (x, y)
                br, bc = int(r) // SIDE, int(col) // SIDE
                if r < 0 or col < 0 or br >= shape[0] or bc >= shape[1] or (br, bc, row["acq_date"]) in seen:
                    continue
                seen.add((br, bc, row["acq_date"]))
                (before if row["acq_date"] < cut else after)[br, bc] += 1
    return before, after


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--tracks", nargs=2, required=True)
    p.add_argument("--cut", default="2026-09-01", help="YYYY-MM-DD: only radar before this day is used, only fire from this day on is counted")
    p.add_argument("--early-db", type=float, default=0.5)
    p.add_argument("--min-days", type=int, default=2)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--firms", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()

    falls, used = [], []
    for track in a.tracks:
        f = last_pass_before(a.layers, a.site, track, a.cut)
        layer, T, epsg = read(f)
        falls.append(-per_block(layer, "median"))
        used.append(f.stem.split("_")[-1])
    fall = (falls[0] + falls[1]) / 2
    early_dry = (falls[0] >= a.early_db) & (falls[1] >= a.early_db)
    peat = per_block(read(a.layers / f"peat_peatmap_{a.site}.tif")[0], "mean") >= 0.5
    canal = per_block(read(a.layers / f"canal_distance_{a.site}.tif")[0], "median")
    before, after = fire_days_by_block(a.firms, T, epsg, fall.shape, a.cut)
    burned = after >= a.min_days
    ok = peat & np.isfinite(fall) & (before == 0)
    y = burned[ok]

    rate_dry, rate_rest = float(y[early_dry[ok]].mean()), float(y[~early_dry[ok]].mean())
    rr, cc = np.where(ok)
    lo, hi, n_tiles = tile_interval(early_dry[ok], y, rr, cc)
    edges = np.nanpercentile(fall[ok], [20, 40, 60, 80])
    fifths = [float(y[np.digitize(fall[ok], edges) == i].mean()) for i in range(5)]
    skill, skill_canal = auc(fall[ok], y), auc(-canal[ok], y)
    note = f"peat blocks of 1 km with no fire before {a.cut}; radar passes used: {used[0]} and {used[1]}; burned later = fire on {a.min_days} or more days from {a.cut} on"
    put(f"hindcast_blocks_{a.site}", int(ok.sum()), "blocks of 1 km", a.site, ME, note=note)
    put(f"hindcast_burned_later_share_{a.site}", float(y.mean()), "share of blocks", a.site, ME)
    put(f"hindcast_early_dry_blocks_{a.site}", int(early_dry[ok].sum()), "blocks of 1 km", a.site, ME, note=f"HH down {a.early_db} dB or more on both orbits by the cut date")
    put(f"hindcast_burned_later_if_early_dry_{a.site}", rate_dry, "share of blocks", a.site, ME)
    put(f"hindcast_burned_later_if_not_{a.site}", rate_rest, "share of blocks", a.site, ME)
    put(f"hindcast_difference_{a.site}", rate_dry - rate_rest, "difference in share", a.site, ME, note=f"95% range {lo:+.2f} to {hi:+.2f}, resampling {n_tiles} tiles of 10 km")
    put(f"hindcast_difference_low_{a.site}", lo, "difference in share", a.site, ME, note="lower end of the 95% range")
    put(f"hindcast_difference_high_{a.site}", hi, "difference in share", a.site, ME, note="upper end of the 95% range")
    put(f"hindcast_burn_rate_by_fifth_{a.site}", ", ".join(f"{v:.2f}" for v in fifths), "share of blocks, least to most early fall", a.site, ME)
    put(f"hindcast_auc_early_fall_{a.site}", skill, "AUC", a.site, ME, note="0.5 is no skill, 1 is perfect")
    put(f"hindcast_auc_canal_distance_{a.site}", skill_canal, "AUC", a.site, ME, note="the simplest alternative: nearer a mapped canal counts as riskier")

    # The same comparison inside drained land only (within 1 km of a mapped canal). Intact forest never
    # dries and rarely burns, so without this the result could be no more than "forest against the rest".
    near = ok & (canal <= 1000)
    if near.sum() > 200 and early_dry[near].any() and (~early_dry[near]).any():
        yn = burned[near]
        dry_n, rest_n = float(yn[early_dry[near]].mean()), float(yn[~early_dry[near]].mean())
        rn, cn = np.where(near)
        lo_n, hi_n, tiles_n = tile_interval(early_dry[near], yn, rn, cn)
        put(f"hindcast_near_canal_difference_{a.site}", dry_n - rest_n, "difference in share", a.site, ME, note=f"95% range {lo_n:+.2f} to {hi_n:+.2f}, resampling {tiles_n} tiles of 10 km")
        put(f"hindcast_near_canal_difference_low_{a.site}", lo_n, "difference in share", a.site, ME)
        put(f"hindcast_near_canal_difference_high_{a.site}", hi_n, "difference in share", a.site, ME)
        put(f"hindcast_near_canal_blocks_{a.site}", int(near.sum()), "blocks of 1 km", a.site, ME, note="the same test on peat within 1 km of a mapped canal only")
        put(f"hindcast_near_canal_burned_later_if_early_dry_{a.site}", dry_n, "share of blocks", a.site, ME)
        put(f"hindcast_near_canal_burned_later_if_not_{a.site}", rest_n, "share of blocks", a.site, ME)
        put(f"hindcast_near_canal_auc_early_fall_{a.site}", auc(fall[near], yn), "AUC", a.site, ME)
        print(f"{a.site}, within 1 km of a canal only: {int(near.sum())} blocks; early fall {dry_n:.0%} burned later against {rest_n:.0%}, "
              f"difference {dry_n - rest_n:+.2f} (95% range {lo_n:+.2f} to {hi_n:+.2f}); AUC {auc(fall[near], yn):.2f}")

    rows = [{"id": f"{a.site}-{r:03d}-{c:03d}", "early_fall_db": round(float(fall[r, c]), 2), "early_dry": bool(early_dry[r, c]),
             "burned_later": bool(burned[r, c]), "fire_days_later": int(after[r, c])} for r, c in np.argwhere(ok)]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"hindcast_{a.site}.json").write_text(json.dumps({"site": a.site, "cut": a.cut, "passes": dict(zip(a.tracks, used)),
                                                             "early_db": a.early_db, "min_days": a.min_days, "blocks": rows}, separators=(",", ":")) + "\n")
    print(f"{a.site}: {int(ok.sum())} peat blocks with no fire before {a.cut}; {y.mean():.0%} burned later. Early fall: {int(early_dry[ok].sum())} blocks, "
          f"{rate_dry:.0%} burned later, against {rate_rest:.0%} of the rest, difference {rate_dry - rate_rest:+.2f} (95% range {lo:+.2f} to {hi:+.2f}). By fifth of early fall: " + " ".join(f"{v:.0%}" for v in fifths) +
          f". AUC {skill:.2f} (canal distance alone {skill_canal:.2f}).")


if __name__ == "__main__":
    main()
