# Written with Super Intelligence (SI) assistance.
"""Where does the method see a fall: under closed forest, or on open and thinly vegetated peat?

The dry-down score is measured against closed forest, so by design it cannot show drying under
closed forest. This step measures how far that goes. It sorts mapped peat by its HV brightness
at the start of the dry season, which rises with the amount of woody vegetation (Mitchard et
al. 2009; Shimada et al. 2014), and reports for each class the share of peat in it, the median
HH change on each orbit, and the share that fell by 1 dB or more on both orbits.

The classes are brightness classes, not a land-cover map. HV also responds to moisture and to
flooding, so the lowest class mixes open ground with water.

    python pipeline/drying/by_cover.py --stacks pipeline/out/stacks --layers pipeline/out/layers \\
        --sites west east --tracks 125 061 --start-from 20260710
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from season import start_passes  # noqa: E402
from vjson import put  # noqa: E402

ME = "pipeline/drying/by_cover.py"
STRONG_DB = -1.0
# HV at the start of the dry season, gamma0 in dB. Edges at 2 dB steps down from the closed reference forest,
# whose median this script writes to validation.json. Round numbers, not tuned; move them and the picture holds.
CLASSES = (("hv_below_m15", -np.inf, -15.0, "HV below -15 dB: open or thinly vegetated"),
           ("hv_m15_m13", -15.0, -13.0, "HV -15 to -13 dB: low or broken woody cover"),
           ("hv_m13_m11", -13.0, -11.0, "HV -13 to -11 dB: open forest and regrowth"),
           ("hv_above_m11", -11.0, np.inf, "HV at or above -11 dB: closed forest"))


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def start_hv(stack_file, start_from):
    """Mean HV over the start passes of the season, in dB."""
    z = np.load(stack_file)
    dates = [str(d) for d in z["dates"]]
    return np.nanmean(z["hv"][start_passes(dates, start_from)], axis=0)


def by_class(hv, changes, peat):
    """For each HV class: share of the peat in it, median change per orbit, share that fell on every orbit."""
    ok = peat & np.isfinite(hv) & np.all([np.isfinite(c) for c in changes], axis=0)
    rows = {}
    for key, low, high, _ in CLASSES:
        m = ok & (hv >= low) & (hv < high)
        if not m.any():
            continue
        fell = np.all([c[m] <= STRONG_DB for c in changes], axis=0)
        rows[key] = {"share": float(m.sum() / ok.sum()), "medians": [float(np.median(c[m])) for c in changes], "fell": float(fell.mean())}
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--sites", nargs="+", required=True)
    p.add_argument("--tracks", nargs=2, required=True, help="ascending then descending")
    p.add_argument("--start-from", help="YYYYMMDD, from pipeline/season.py")
    a = p.parse_args()
    for site in a.sites:
        peat_file = a.layers / f"peat_peatmap_{site}.tif"
        if not peat_file.exists():
            print(f"{site}: no peat layer, skipped")
            continue
        hv = start_hv(a.stacks / f"{site}_{a.tracks[0]}.npz", a.start_from)
        changes = [read(a.layers / f"drydown_{site}_{t}.tif") for t in a.tracks]
        rows = by_class(hv, changes, read(peat_file) == 1)
        for key, _, _, words in CLASSES:
            if key not in rows:
                continue
            r = rows[key]
            put(f"cover_peat_share_{key}_{site}", r["share"], "share of mapped peat", site, ME, note=words)
            put(f"cover_fell_share_{key}_{site}", r["fell"], "share of class", site, ME, note="fell by 1 dB or more on both orbits")
            for track, median in zip(a.tracks, r["medians"]):
                put(f"cover_median_hh_change_{key}_{site}_{track}", median, "dB", site, ME, note="median HH change over the dry season, against closed forest")
            print(f"{site} {words}: {r['share']:.0%} of peat, median HH change {r['medians'][0]:+.2f} and {r['medians'][1]:+.2f} dB, {r['fell']:.0%} fell on both orbits")
        if site == "west" and (a.layers / "reference_west.tif").exists():
            ref = read(a.layers / "reference_west.tif") == 1
            put(f"reference_start_hv_median_{a.tracks[0]}", float(np.nanmedian(hv[ref])), "dB", site, ME, note="HV of the closed reference forest at the start of the dry season")
            print(f"closed reference forest: median start HV {np.nanmedian(hv[ref]):.1f} dB")


if __name__ == "__main__":
    main()
