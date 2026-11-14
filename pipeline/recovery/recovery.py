# Written with Super Intelligence (SI) assistance.
"""Recovery after the rain (track 2b).

When the rain comes back, wet ground brightens again in HH. Vegetation that was lost does
not come back in days, so HV tells a different story. For one site and one track with at
least one pass after the rain, on 250 m blocks and with the scene-wide shift removed:

  fall      late dry season minus start of season   (the dry-down, as in pipeline/drying)
  rebound   first pass after the rain minus late dry season
  left      first pass after the rain minus start of season (what the rain did not bring back)

Writes recovery_<pol>_<site>_<track>.tif (the rebound) and recovery_left_<pol>_<site>_<track>.tif
(what is left, the third beat of the story) for HH and HV, in decibels, and numbers in validation.json for the blocks that fell by 1 dB or more on both
orbits, also split on and off mapped peat and into burnt and only dried once the peat and
fire layers exist. Run it once per track. When both tracks have a pass after the rain, the second run
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
from season import start_passes  # noqa: E402

ME = "pipeline/recovery/recovery.py"
STRONG_DB = -1.0
MIN_ZONE_BLOCKS = 100   # fewer strongly dried blocks than this in a group and its medians are not reported


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def recover(stack, base, dry_until, late_n=2, late_skip=0, wet_pass=0, start_from=None):
    """Fall, rebound and left for HH and HV on 250 m blocks, or None if no pass is after dry_until.

    late_n is how many of the last dry passes make "late season", and late_skip how many of the very
    last dry passes to leave out of it; wet_pass picks which pass after the rain to use (0 is the
    first). The defaults are what the layers and validation.json use.

    Returns (out, dry, after): out[pol] holds the three arrays, dry the indices of the dry-season
    passes and after the index of the first pass after the rain."""
    dry = [i for i, d in enumerate(stack["dates"]) if d <= dry_until]
    wet = [i for i, d in enumerate(stack["dates"]) if d > dry_until]
    if len(wet) <= wet_pass:
        return None
    if len(dry) < 4:
        raise SystemExit("need at least four passes on or before --dry-until, so the start and late pairs do not overlap")
    after = wet[wet_pass]
    out = {}
    for pol in ("hh", "hv"):
        layers = normalised(stack, base, pol)
        start = np.mean([block_mean(layers[i]) for i in start_passes(stack["dates"], start_from)], axis=0)
        late = np.mean([block_mean(layers[i]) for i in dry[len(dry) - late_skip - late_n:len(dry) - late_skip]], axis=0)
        wet_level = block_mean(layers[after])
        out[pol] = {"fall": late - start, "rebound": wet_level - late, "left": wet_level - start}
    return out, dry, after


def strong_blocks(out, fall_other, cov):
    """One sample per 250 m block (the centre pixel of each 5 by 5), and those that fell by 1 dB or more in HH on both orbits."""
    pick = np.zeros(cov.shape, bool)
    pick[2::5, 2::5] = True
    ok = pick & cov & np.isfinite(fall_other) & np.isfinite(out["hh"]["rebound"]) & np.isfinite(out["hv"]["rebound"])
    return ok, ok & (out["hh"]["fall"] < STRONG_DB) & (fall_other < STRONG_DB)


def zones(peat, fire):
    """The four groups the recovery is reported in: on or off mapped peat, and burnt or only dried.

    peat is True on mapped peat, fire True within 200 m of a 2026 fire detection (split.py's rules).
    Burnt land should come back in HH, the ground is wet again, but not in HV, the canopy is gone."""
    return {f"{pz}_{fz}": p & f for pz, p in (("on_peat", peat), ("off_peat", ~peat)) for fz, f in (("no_fire", ~fire), ("fire", fire))}


def summarise(pol_out, strong, floor):
    """Medians over the strongly dried blocks, the share of the fall regained, and the share back within the noise floor."""
    fall, rebound, left = (pol_out[k][strong] for k in ("fall", "rebound", "left"))
    regained = float(np.median(rebound) / -np.median(fall)) if np.median(fall) < 0 else float("nan")
    return {"fall": float(np.median(fall)), "rebound": float(np.median(rebound)), "left": float(np.median(left)),
            "regained": regained, "back": float((left > -floor).mean())}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--track", required=True, help="the track that has a pass after the rain")
    p.add_argument("--other-track", required=True, help="the other orbit, used as an independent measure of the fall")
    p.add_argument("--dry-until", required=True, help="YYYYMMDD, last day before the rain returned")
    p.add_argument("--start-from", help="YYYYMMDD, earliest day for a start pass (pipeline/season.py); default: the first two passes")
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--peat", default="peat_peatmap", help="name stem of the peat layer, as in pipeline/drying/split.py")
    a = p.parse_args()
    stack = load_stack(a.stacks / f"{a.site}_{a.track}.npz")
    base = json.loads((a.layers / f"baseline_{a.track}.json").read_text())
    res = recover(stack, base, a.dry_until, start_from=a.start_from)
    if res is None:
        print(f"{a.site} track {a.track}: no pass after {a.dry_until} yet, skipped")
        return
    out, dry, after = res
    for pol in ("hh", "hv"):
        passes = {"track": a.track, "after_pass": stack["dates"][after], "start_passes": ",".join(stack["dates"][i] for i in start_passes(stack["dates"], a.start_from)),
                  "late_passes": ",".join(stack["dates"][i] for i in dry[-2:])}
        for kind, name, title in (("rebound", f"recovery_{pol}", "rebound after the rain"),
                                  ("left", f"recovery_left_{pol}", "left after the rain against the start of the season")):
            layer = out[pol][kind].astype("float32")
            layer[~stack["cov"]] = np.nan
            write_layer(a.layers / f"{name}_{a.site}_{a.track}.tif", layer, stack, layer=f"{pol.upper()} {title}", units="dB", **passes)

    # Blocks that fell by 1 dB or more in HH on both orbits; the other orbit's fall is independent of this track.
    fall_other = read(a.layers / f"drydown_{a.site}_{a.other_track}.tif")
    ok, strong = strong_blocks(out, fall_other, stack["cov"])
    floor = abs(get(f"noise_floor_hh_{a.track}")["value"])
    n = int(strong.sum())
    tag = f"{a.site}_{a.track}"
    put(f"recovery_blocks_{tag}", n, "blocks of 250 m", a.site, ME, note=f"fell by 1 dB or more in HH on both orbits; pass after the rain: {stack['dates'][after]}")
    r = float(np.corrcoef(out["hh"]["rebound"][ok], fall_other[ok])[0, 1])
    put(f"recovery_rebound_vs_other_orbit_fall_r_{tag}", r, "Pearson r", a.site, ME,
        note="HH rebound on this track against the fall measured by the other orbit; negative means what dried most came back most")
    print(f"{a.site} track {a.track}: pass after the rain {stack['dates'][after]}, {n} strongly dried blocks, rebound against other-orbit fall r = {r:.2f}")
    for pol in ("hh", "hv"):
        m = summarise(out[pol], strong, floor)
        put(f"recovery_{pol}_median_fall_{tag}", m["fall"], "dB", a.site, ME)
        put(f"recovery_{pol}_median_rebound_{tag}", m["rebound"], "dB", a.site, ME)
        put(f"recovery_{pol}_median_left_{tag}", m["left"], "dB", a.site, ME, note="level after the rain against the start of the season")
        put(f"recovery_{pol}_share_regained_{tag}", m["regained"], "share of the fall", a.site, ME)
        put(f"recovery_{pol}_share_back_within_noise_{tag}", m["back"], "share of blocks", a.site, ME)
        print(f"   {pol.upper()}: median fall {m['fall']:+.2f} dB, rebound {m['rebound']:+.2f} dB, still {m['left']:+.2f} dB from the start; "
              f"{m['regained']:.0%} of the fall regained; {m['back']:.0%} of blocks back within the noise floor")

    # The same, on and off mapped peat, and burnt apart from only dried, once track 3's layers exist.
    peat_file, fire_file = a.layers / f"{a.peat}_{a.site}.tif", a.layers / f"fire_days_{a.site}.tif"
    if peat_file.exists() and fire_file.exists():
        peat, fire = read(peat_file) == 1, np.nan_to_num(read(fire_file)) > 0
        if peat.shape != strong.shape:
            raise SystemExit(f"{peat_file.name} is not on the grid of the stack")
        for zone, mask in zones(peat, fire).items():
            s = strong & mask
            put(f"recovery_blocks_{zone}_{tag}", int(s.sum()), "blocks of 250 m", a.site, ME, note="fell by 1 dB or more in HH on both orbits")
            if s.sum() < MIN_ZONE_BLOCKS:
                print(f"   {zone}: {int(s.sum())} blocks, too few to report")
                continue
            line = f"   {zone:17s} {int(s.sum()):6d} blocks:"
            for pol in ("hh", "hv"):
                m = summarise(out[pol], s, floor)
                put(f"recovery_{pol}_share_regained_{zone}_{tag}", m["regained"], "share of the fall", a.site, ME)
                put(f"recovery_{pol}_median_left_{zone}_{tag}", m["left"], "dB", a.site, ME, note="level after the rain against the start of the season")
                line += f"  {pol.upper()} {m['regained']:.0%} regained, {m['left']:+.2f} dB left"
            print(line)
    else:
        print(f"   {peat_file.name} or {fire_file.name} is not there yet, no split by peat and fire")

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
