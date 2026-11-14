# Written with Super Intelligence (SI) assistance.
"""Step 3 of drying: the noise floor, and which blocks dried beyond it on both orbits.

How much does the dry-down score move where nothing is drying? We measure it on the intact
reference forest: the 5th percentile of the score over forest blocks is the noise floor for
that track. A block counts as dried only if it fell below the floor on the ascending track
and on the descending track. The two tracks look from opposite sides at different times of
day, so a change they both see is unlikely to be an artefact of either.

Writes dried_<site>.tif (1 dried, 0 not, NaN no data) and entries in validation.json.

    python pipeline/drying/noise_floor.py --layers pipeline/out/layers --sites west east --tracks 125 061
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import BLOCK, block_mean  # noqa: E402
from vjson import put  # noqa: E402

ME = "pipeline/drying/noise_floor.py"
KM2 = 0.0025   # one 50 m pixel


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--layers", required=True, type=Path, help="folder with the drydown and reference layers")
    p.add_argument("--sites", nargs="+", required=True)
    p.add_argument("--tracks", nargs=2, required=True, metavar=("ASCENDING", "DESCENDING"))
    p.add_argument("--reference-site", default="west")
    a = p.parse_args()

    # Blocks that are reference forest through and through, one sample per block so samples do not overlap.
    ref, _ = read(a.layers / f"reference_{a.reference_site}.tif")
    solid = block_mean(ref) > 0.95
    pick = np.zeros_like(solid)
    pick[BLOCK // 2::BLOCK, BLOCK // 2::BLOCK] = True

    floors = {}
    for track in a.tracks:
        score, _ = read(a.layers / f"drydown_{a.reference_site}_{track}.tif")
        v = score[solid & pick & np.isfinite(score)]
        p5, p50, p95 = (float(x) for x in np.percentile(v, [5, 50, 95]))
        floors[track] = p5
        put(f"noise_floor_hh_{track}", p5, "dB", a.reference_site, ME,
            note=f"5th percentile of the dry-down score over {v.size} intact-forest blocks of 250 m")
        put(f"reference_drydown_median_{track}", p50, "dB", a.reference_site, ME)
        put(f"reference_drydown_p95_{track}", p95, "dB", a.reference_site, ME)
        print(f"track {track}: {v.size} forest blocks, score p5 {p5:.2f} median {p50:.2f} p95 {p95:.2f} dB")

    for site in a.sites:
        scores = {}
        for track in a.tracks:
            scores[track], profile = read(a.layers / f"drydown_{site}_{track}.tif")
        valid = np.all([np.isfinite(s) for s in scores.values()], axis=0)
        below = {t: valid & (scores[t] < floors[t]) for t in a.tracks}
        dried = below[a.tracks[0]] & below[a.tracks[1]]
        out = np.where(valid, dried.astype("float32"), np.nan)
        with rasterio.open(a.layers / f"dried_{site}.tif", "w", **profile) as dst:
            dst.write(out.astype("float32"), 1)
            dst.update_tags(layer="dried on both orbits", **{f"floor_{t}": f"{floors[t]:.4f}" for t in a.tracks})
        put(f"valid_km2_{site}", float(valid.sum() * KM2), "km2", site, ME)
        put(f"dried_both_orbits_km2_{site}", float(dried.sum() * KM2), "km2", site, ME,
            note="not yet split into on and off mapped peat")
        put(f"dried_both_orbits_share_{site}", float(dried.sum() / valid.sum()), "share of valid area", site, ME)
        for t in a.tracks:
            put(f"dried_one_orbit_share_{site}_{t}", float(below[t].sum() / valid.sum()), "share of valid area", site, ME)
        print(f"{site}: valid {valid.sum() * KM2:.0f} km2, below floor on {a.tracks[0]} {below[a.tracks[0]].mean() / valid.mean():.1%}, "
              f"on {a.tracks[1]} {below[a.tracks[1]].mean() / valid.mean():.1%}, on both {dried.sum() / valid.sum():.1%} ({dried.sum() * KM2:.0f} km2)")

    # How much of the reference forest itself gets flagged: should be small.
    dried_ref, _ = read(a.layers / f"dried_{a.reference_site}.tif")
    share = float(np.nanmean(dried_ref[solid]))
    put("reference_flagged_share", share, "share of reference forest", a.reference_site, ME,
        note="share of the intact reference forest that the dried rule flags; a false-alarm rate")
    print(f"reference forest flagged as dried: {share:.1%}")


if __name__ == "__main__":
    main()
