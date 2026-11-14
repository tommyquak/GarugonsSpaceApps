# Written with Super Intelligence (SI) assistance.
"""Recovery after the rain (track 2b).

When the rain comes back, wet ground brightens again in HH. Vegetation that was lost does
not come back in days, so HV tells a different story. For one site and one track with at
least one pass after the rain, on 250 m blocks and with the scene-wide shift removed:

  fall      late dry season minus start of season   (the dry-down, as in pipeline/drying)
  rebound   first pass after the rain minus late dry season
  left      first pass after the rain minus start of season (what the rain did not bring back)

Writes recovery_hh_<site>_<track>.tif and recovery_hv_<site>_<track>.tif (the rebound, in
decibels), and numbers in validation.json for the blocks that fell by 1 dB or more on both
orbits. Run it once per track. When both tracks have a pass after the rain, the second run
also compares the two rebounds: they are measured days apart from opposite sides, so
agreement between them is evidence that the rebound is on the ground and not in the radar.

    python pipeline/recovery/recovery.py --site west --track 125 --other-track 061 --dry-until 20261025 \\
        --stacks pipeline/out/stacks --layers pipeline/out/layers
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
from common import block_mean, load_stack, write_layer  # noqa: E402
from drydown import normalised  # noqa: E402
from vjson import get, put  # noqa: E402

ME = "pipeline/recovery/recovery.py"
STRONG_DB = -1.0


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--track", required=True, help="the track that has a pass after the rain")
    p.add_argument("--other-track", required=True, help="the other orbit, used as an independent measure of the fall")
    p.add_argument("--dry-until", required=True, help="YYYYMMDD, last day before the rain returned")
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stacks / f"{a.site}_{a.track}.npz")
    base = json.loads((a.layers / f"baseline_{a.track}.json").read_text())
    dry = [i for i, d in enumerate(stack["dates"]) if d <= a.dry_until]
    wet = [i for i, d in enumerate(stack["dates"]) if d > a.dry_until]
    if not wet:
        print(f"{a.site} track {a.track}: no pass after {a.dry_until} yet, skipped")
        return
    after = wet[0]
    out = {}
    for pol in ("hh", "hv"):
        layers = normalised(stack, base, pol)
        start = np.mean([block_mean(layers[i]) for i in dry[:2]], axis=0)
        late = np.mean([block_mean(layers[i]) for i in dry[-2:]], axis=0)
        wet_level = block_mean(layers[after])
        out[pol] = {"fall": late - start, "rebound": wet_level - late, "left": wet_level - start}
        rebound = out[pol]["rebound"].astype("float32")
        rebound[~stack["cov"]] = np.nan
        write_layer(a.layers / f"recovery_{pol}_{a.site}_{a.track}.tif", rebound, stack, layer=f"{pol.upper()} rebound after the rain", units="dB",
                    track=a.track, after_pass=stack["dates"][after], late_passes=",".join(stack["dates"][i] for i in dry[-2:]))

    # Blocks that fell by 1 dB or more in HH on both orbits; the other orbit's fall is independent of this track.
    fall_other = read(a.layers / f"drydown_{a.site}_{a.other_track}.tif")
    pick = np.zeros(stack["cov"].shape, bool)
    pick[2::5, 2::5] = True
    ok = pick & stack["cov"] & np.isfinite(fall_other) & np.isfinite(out["hh"]["rebound"]) & np.isfinite(out["hv"]["rebound"])
    strong = ok & (out["hh"]["fall"] < STRONG_DB) & (fall_other < STRONG_DB)
    floor = abs(get(f"noise_floor_hh_{a.track}")["value"])
    n = int(strong.sum())
    tag = f"{a.site}_{a.track}"
    put(f"recovery_blocks_{tag}", n, "blocks of 250 m", a.site, ME, note=f"fell by 1 dB or more in HH on both orbits; pass after the rain: {stack['dates'][after]}")
    r = float(np.corrcoef(out["hh"]["rebound"][ok], fall_other[ok])[0, 1])
    put(f"recovery_rebound_vs_other_orbit_fall_r_{tag}", r, "Pearson r", a.site, ME,
        note="HH rebound on this track against the fall measured by the other orbit; negative means what dried most came back most")
    print(f"{a.site} track {a.track}: pass after the rain {stack['dates'][after]}, {n} strongly dried blocks, rebound against other-orbit fall r = {r:.2f}")
    for pol in ("hh", "hv"):
        fall, rebound, left = (out[pol][k][strong] for k in ("fall", "rebound", "left"))
        regained = float(np.median(rebound) / -np.median(fall)) if np.median(fall) < 0 else float("nan")
        back = float((left > -floor).mean())
        put(f"recovery_{pol}_median_fall_{tag}", float(np.median(fall)), "dB", a.site, ME)
        put(f"recovery_{pol}_median_rebound_{tag}", float(np.median(rebound)), "dB", a.site, ME)
        put(f"recovery_{pol}_median_left_{tag}", float(np.median(left)), "dB", a.site, ME, note="level after the rain against the start of the season")
        put(f"recovery_{pol}_share_regained_{tag}", regained, "share of the fall", a.site, ME)
        put(f"recovery_{pol}_share_back_within_noise_{tag}", back, "share of blocks", a.site, ME)
        print(f"   {pol.upper()}: median fall {np.median(fall):+.2f} dB, rebound {np.median(rebound):+.2f} dB, still {np.median(left):+.2f} dB from the start; "
              f"{regained:.0%} of the fall regained; {back:.0%} of blocks back within the noise floor")


    # If the other orbit already has its own rebound layer, compare the two.
    other = a.layers / f"recovery_hh_{a.site}_{a.other_track}.tif"
    if other.exists():
        mine, theirs = out["hh"]["rebound"], read(other)
        k = strong & np.isfinite(theirs)
        if k.sum() > 100:
            r_strong = float(np.corrcoef(mine[k], theirs[k])[0, 1])
            k_all = ok & np.isfinite(theirs)
            r_all = float(np.corrcoef(mine[k_all], theirs[k_all])[0, 1])
            pair = "_".join(sorted([a.track, a.other_track]))
            put(f"recovery_hh_two_orbit_r_{a.site}_{pair}", r_all, "Pearson r", a.site, ME, note="HH rebound of one orbit against the other, all blocks")
            put(f"recovery_hh_two_orbit_r_strong_{a.site}_{pair}", r_strong, "Pearson r", a.site, ME, note="the same, only blocks that fell by 1 dB or more on both orbits")
            print(f"   two orbits' HH rebound agree at r = {r_all:.2f} over all blocks, {r_strong:.2f} over the strongly dried ones "
                  f"(medians {np.median(mine[k]):+.2f} and {np.median(theirs[k]):+.2f} dB)")


if __name__ == "__main__":
    main()
