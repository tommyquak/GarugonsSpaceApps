# Written with Super Intelligence (SI) assistance.
"""Coherence burn flag: where the radar echo stopped matching itself between two passes, checked against fire detections.

Interferometric coherence says how alike the echo of a place was on two passes of the same
track, from 0 to 1. Fire changes the ground between passes and should pull it down for the pair
that spans the fire. So do clearing, harvest and flooding, so a drop alone is not a fire.

For one site and one track, from the GUNW coherence pulled by pull_gunw.py:

  1. Only pairs 12 days apart are used: coherence falls with the time between passes, so
     longer pairs would look like drops everywhere.
  2. Each pair's coherence is put on the dry-down grid, and its scene-wide level is removed:
     the median over cells with no fire detection within 1 km all season.
  3. A cell's drop in a pair is its level in that pair minus its median over the pairs that
     do not span a fire detection at that cell (at least 3 are needed).
  4. A cell is flagged when its largest drop over the season is beyond what 95% of the cells
     with no fire within 1 km show. Five per cent of such cells are flagged by construction:
     that is how the threshold is set, not a measured false-alarm rate, since FIRMS decides
     which cells count as without fire (and FIRMS also sets each cell's usual level in step 3).
  5. The flag is checked against NASA FIRMS, on mapped peat and off it: how much of the land
     with a fire detection during a 12-day pair is flagged (hit rate); how much of the flagged
     land had a detection within 1 km between the first and last passes, gaps between pairs
     included (against the share of all land that did); and, for flagged land with fire during
     a pair, how often the largest drop is in a pair that spans a detection there (any one,
     not only the first), against the share of its pairs that do.

Writes <layers>/coh_drop_<site>_<track>.tif (the largest drop) and
<layers>/burn_flag_<site>_<track>.tif (1 flagged, 0 not, NaN no data), and coh_* keys to
validation.json, all exploratory.

    python pipeline/context/burn_flag.py --site west --track 125 --gunw data/gunw/west \\
        --firms data/firms/west --layers pipeline/out/layers
"""
import argparse
import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vjson import put  # noqa: E402
from fire_layers import KM2, PIXEL_M, WIDE_REACH_M, count_days, on_grid, read_detections  # noqa: E402

ME = "pipeline/context/burn_flag.py"
PAIR_DAYS = 12
MIN_CLEAR_PAIRS = 3
FALSE_ALARM = 0.05
ZONES = ("on_peat", "off_peat")


def days_between(ref, sec):
    return (dt.datetime.strptime(sec, "%Y%m%d") - dt.datetime.strptime(ref, "%Y%m%d")).days


def load_pairs(folder, track, profile):
    """12-day coherence pairs of one track on the grid of `profile`, as (list of (ref, sec), array pairs x rows x cols)."""
    pairs, layers = [], []
    for f in sorted(Path(folder).glob("*_coh.tif")):
        with rasterio.open(f) as src:
            tags = src.tags()
            if int(tags["track_number"]) != int(track):
                continue
            ref, sec = tags["reference_date"], tags["secondary_date"]
            if days_between(ref, sec) != PAIR_DAYS:
                continue
            out = np.full((profile["height"], profile["width"]), np.nan, "float32")
            finer = abs(src.transform.a) < PIXEL_M
            reproject(src.read(1), out, src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
                      dst_transform=profile["transform"], dst_crs=profile["crs"], dst_nodata=np.nan,
                      resampling=Resampling.average if finer else Resampling.bilinear)
            pairs.append((ref, sec))
            layers.append(out)
    order = np.argsort([p[0] for p in pairs])
    return [pairs[i] for i in order], np.stack([layers[i] for i in order]) if layers else None


def fire_masks(by_day, pairs, shape):
    """For each pair, the cells a detection's footprint reached after the first pass and up to the second."""
    edge = WIDE_REACH_M // PIXEL_M
    out = []
    for ref, sec in pairs:
        window = {d: v for d, v in by_day.items() if ref < d.replace("-", "") <= sec}
        out.append(count_days(window, shape, edge)[0] > 0)
    return np.stack(out)


def drops(coh, fire, never):
    """Each pair's level against the cell's own median over its pairs without fire, after removing each pair's scene-wide level."""
    level = coh - np.array([np.nanmedian(c[never]) for c in coh], "float32")[:, None, None]
    clear = np.where(fire, np.nan, level)
    enough = np.isfinite(clear).sum(0) >= MIN_CLEAR_PAIRS
    with warnings.catch_warnings():     # cells with no clear pair at all are left out just below
        warnings.simplefilter("ignore", RuntimeWarning)
        typical = np.nanmedian(clear, axis=0)
    d = level - typical[None]
    d[:, ~enough] = np.nan
    return d


def check(largest, flag, fire_any, near_fire, timing_ok, fire_pair_share, zone):
    """Hit rate, flagged land with fire nearby against all land with fire nearby, and timing against luck, inside one zone.
    `fire_pair_share` is, per cell, the share of its pairs that span a fire: the chance its largest drop lands on one by luck."""
    ok = zone & np.isfinite(largest)
    hits = flag & fire_any & ok
    return {"hit_rate": float(hits.sum() / max((fire_any & ok).sum(), 1)),
            "flag_share": float((flag & ok).sum() / max(ok.sum(), 1)),
            "flag_near_fire": float((flag & near_fire & ok).sum() / max((flag & ok).sum(), 1)),
            "all_near_fire": float((near_fire & ok).sum() / max(ok.sum(), 1)),
            "timing": float((hits & timing_ok).sum() / max(hits.sum(), 1)),
            "timing_chance": float(fire_pair_share[hits].mean()) if hits.any() else float("nan"),
            "flag_no_fire_km2": float((flag & ~near_fire & ok).sum() * KM2)}


def two_orbits(flag_a, flag_b, drop_a, drop_b, zone):
    """Of the land flagged on one orbit, the share flagged on the other, against the other's flag share; and the rank
    correlation of the two largest-drop maps. The orbits look from opposite sides, hours apart."""
    k = zone & np.isfinite(flag_a) & np.isfinite(flag_b)
    fa, fb = (flag_a == 1) & k, (flag_b == 1) & k
    both = np.isfinite(drop_a) & np.isfinite(drop_b) & zone
    return {"overlap": float((fa & fb).sum() / max(fa.sum(), 1)), "other_share": float(fb.sum() / max(k.sum(), 1)),
            "spearman": float(spearmanr(drop_a[both], drop_b[both])[0]) if both.sum() > 100 else float("nan")}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--track", required=True, help="125 or 061")
    p.add_argument("--gunw", required=True, type=Path, help="folder written by pull_gunw.py for this site")
    p.add_argument("--firms", required=True, type=Path, help="folder written by pull_firms.py for this site")
    p.add_argument("--layers", required=True, type=Path, help="folder with drydown_<site>_<track>.tif and peat_peatmap_<site>.tif")
    p.add_argument("--other-track", help="if that track's burn flag is already in --layers, compare the two orbits")
    a = p.parse_args(argv)
    tag = f"{a.site}_{a.track}"
    with rasterio.open(a.layers / f"drydown_{tag}.tif") as src:
        profile = src.profile.copy()
    with rasterio.open(a.layers / f"peat_peatmap_{a.site}.tif") as src:
        peat = src.read(1) == 1
    pairs, coh = load_pairs(a.gunw, a.track, profile)
    if coh is None or len(pairs) < MIN_CLEAR_PAIRS + 1:
        raise SystemExit(f"{tag}: {len(pairs)} 12-day pairs in {a.gunw}, need at least {MIN_CLEAR_PAIRS + 1}")
    shape = coh.shape[1:]
    by_day = on_grid(read_detections(a.firms), profile["transform"], profile["crs"].to_epsg(), shape)
    fire = fire_masks(by_day, pairs, shape)
    start, end = pairs[0][0], pairs[-1][1]
    season = {d: v for d, v in by_day.items() if start < d.replace("-", "") <= end}
    near_fire = count_days(season, shape, WIDE_REACH_M // PIXEL_M)[1] > 0      # within 1 km, first to last pass, gaps included
    never = ~(count_days(by_day, shape, WIDE_REACH_M // PIXEL_M)[1] > 0)       # no fire within 1 km all season
    fire_any = fire.any(0)

    d = drops(coh, fire, never)
    have = np.isfinite(d).any(0)
    largest = np.where(have, np.nanmin(np.where(np.isfinite(d), d, np.inf), axis=0), np.nan).astype("float32")
    threshold = float(np.nanpercentile(largest[never & have], 100 * FALSE_ALARM))
    flag = have & (largest < threshold)
    worst = np.argmin(np.where(np.isfinite(d), d, np.inf), axis=0)
    timing_ok = np.take_along_axis(fire, worst[None], 0)[0]
    usable = np.isfinite(d)
    fire_pair_share = (fire & usable).sum(0) / np.maximum(usable.sum(0), 1)

    out = {**profile, "dtype": "float32", "nodata": np.nan}
    for name, layer, text in ((f"coh_drop_{tag}.tif", largest, "largest drop in 12-day coherence against the cell's own pairs without fire"),
                              (f"burn_flag_{tag}.tif", np.where(have, flag, np.nan).astype("float32"), "1 where the largest coherence drop is beyond 95% of never-fire cells")):
        with rasterio.open(a.layers / name, "w", **out) as dst:
            dst.write(layer, 1)
            dst.update_tags(layer=text, source="NISAR L2 GUNW coherence; NASA FIRMS for the check", pairs=" ".join(f"{r}-{s}" for r, s in pairs))

    fire_d = d[fire & np.isfinite(d)]
    clear_d = d[~fire & np.isfinite(d) & never[None]]
    put(f"coh_pairs_{tag}", len(pairs), "12-day pairs", a.site, ME, note=f"{start} to {end}")
    put(f"coh_threshold_{tag}", threshold, "coherence", a.site, ME, note="largest drop beyond which 5% of never-fire cells fall")
    put(f"coh_drop_median_fire_pairs_{tag}", float(np.median(fire_d)) if fire_d.size else float("nan"), "coherence", a.site, ME,
        note="median drop in pairs that span a fire detection at the cell")
    put(f"coh_drop_median_clear_pairs_{tag}", float(np.median(clear_d)), "coherence", a.site, ME, note="the same in never-fire cells")
    print(f"{tag}: {len(pairs)} 12-day pairs {start} to {end}; threshold {threshold:+.3f}; median drop "
          f"{np.median(fire_d) if fire_d.size else float('nan'):+.3f} in pairs spanning a fire against {np.median(clear_d):+.3f} without")
    for zone, mask in zip(ZONES, (peat, ~peat)):
        m = check(largest, flag, fire_any, near_fire, timing_ok, fire_pair_share, mask)
        put(f"coh_flag_hit_rate_{zone}_{tag}", m["hit_rate"], "share of land with fire", a.site, ME, note="land with a fire detection during a 12-day pair that is flagged")
        put(f"coh_flag_share_{zone}_{tag}", m["flag_share"], "share of zone", a.site, ME)
        put(f"coh_flag_near_fire_{zone}_{tag}", m["flag_near_fire"], "share of flagged land", a.site, ME,
            note="flagged land with a fire detection within 1 km between the first and last passes, gaps included; compare with coh_all_near_fire")
        put(f"coh_all_near_fire_{zone}_{tag}", m["all_near_fire"], "share of zone", a.site, ME)
        put(f"coh_flag_timing_{zone}_{tag}", m["timing"], "share of flagged fire land", a.site, ME,
            note="flagged land with fire during a 12-day pair whose largest drop is in a pair that spans a detection there (any one, not only the first); compare with coh_flag_timing_chance")
        put(f"coh_flag_timing_chance_{zone}_{tag}", m["timing_chance"], "share of flagged fire land", a.site, ME,
            note="the same if the largest drop fell on a random pair of the cell")
        put(f"coh_flag_no_fire_km2_{zone}_{tag}", m["flag_no_fire_km2"], "km2", a.site, ME,
            note="flagged with no fire detection within 1 km: clearing, harvest, flooding or fire FIRMS missed")
        print(f"   {zone.replace('_', ' ')}: {m['hit_rate']:.0%} of land with fire flagged; {m['flag_share']:.0%} of the zone flagged, "
              f"{m['flag_near_fire']:.0%} of it near fire against {m['all_near_fire']:.0%} of all land; "
              f"timing right for {m['timing']:.0%} (luck: {m['timing_chance']:.0%}); {m['flag_no_fire_km2']:.0f} km2 flagged far from fire")

    # The other orbit, if its flag is already there: the same ground seen from the other side, hours apart.
    if a.other_track and (a.layers / f"burn_flag_{a.site}_{a.other_track}.tif").exists():
        def read(name):
            with rasterio.open(a.layers / name) as src:
                return src.read(1)
        flag_mine = np.where(have, flag, np.nan).astype("float32")
        flag_other, drop_other = read(f"burn_flag_{a.site}_{a.other_track}.tif"), read(f"coh_drop_{a.site}_{a.other_track}.tif")
        pair = "_".join(sorted([a.track, a.other_track]))
        for zone, mask in zip(ZONES, (peat, ~peat)):
            o = two_orbits(flag_other, flag_mine, drop_other, largest, mask)
            put(f"coh_flag_two_orbit_overlap_{zone}_{a.site}_{pair}", o["overlap"], "share of flagged land", a.site, ME,
                note=f"land flagged on track {a.other_track} that track {a.track} flags too; compare with coh_flag_share_{zone}_{tag}")
            put(f"coh_drop_two_orbit_spearman_{zone}_{a.site}_{pair}", o["spearman"], "Spearman r", a.site, ME,
                note="largest coherence drop of one orbit against the other's")
            print(f"   two orbits, {zone.replace('_', ' ')}: {o['overlap']:.0%} of the land track {a.other_track} flags is flagged here too "
                  f"(here {o['other_share']:.0%} of all such land is); largest drops agree at Spearman r {o['spearman']:.2f}")


if __name__ == "__main__":
    main()
