# Written with Super Intelligence (SI) assistance.
"""Repeat fire: did the land with fire in 2026 also have fire in earlier fire seasons?

Compares the 2026 fire layer (fire_days_<site>.tif) with NASA FIRMS detections from earlier
seasons, pulled into one folder per year with pull_firms.py. Earlier detections are read with
the same rules as fire_layers.py: low-confidence ones dropped, each marking the cells within
half its own pixel size.

Writes <layers>/fire_years_<site>.tif, the number of earlier seasons with a detection whose
footprint reaches each cell, and to validation.json, on mapped peat (PEATMAP) and off it:

  fire_share_<zone>_<year>_<site>    share of the zone with fire in that season, one per year
  fire_earlier_share_<zone>_<site>   share of the zone with fire in any earlier season pulled
  fire_repeat_share_<zone>_<site>    share of the 2026 fire in the zone that had fire in an earlier season
  fire_new_km2_<zone>_<site>         2026 fire in the zone with no fire in any earlier season pulled

If 2026 fire fell on land regardless of its past, the repeat share would equal the earlier
share; the gap between the two is what this measures. Earlier seasons were seen by fewer
satellites (VIIRS on NOAA-20 from 2018, NOAA-21 from 2023), so earlier fire is if anything
undercounted. These are active-fire detections, not burnt area.

    FIRMS_MAP_KEY=... python pipeline/context/pull_firms.py --site west --start 2015-07-01 --end 2015-11-30 \\
        --out data/firms_history/west/2015
    python pipeline/context/repeat_fire.py --site west --history data/firms_history/west --layers pipeline/out/layers
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vjson import put  # noqa: E402
from fire_layers import KM2, PIXEL_M, SOURCE, WIDE_REACH_M, count_days, on_grid, read_detections  # noqa: E402

ME = "pipeline/context/repeat_fire.py"
ZONES = ("on_peat", "off_peat")


def season(folder, T, epsg, shape):
    """Cells reached by a detection's footprint in one season's FIRMS files, and how many detections were kept."""
    detections = read_detections(folder)
    days, _ = count_days(on_grid(detections, T, epsg, shape), shape, WIDE_REACH_M // PIXEL_M)
    return days > 0, len(detections)


def summarise(now, earlier, peat):
    """Per zone: share with earlier fire, share of the 2026 fire that is repeat fire, and new 2026 fire in km2."""
    out = {}
    for zone, mask in zip(ZONES, (peat, ~peat)):
        burnt = now & mask
        out[zone] = {"earlier_share": float((earlier & mask).sum() / max(mask.sum(), 1)),
                     "repeat_share": float((burnt & earlier).sum() / max(burnt.sum(), 1)),
                     "new_km2": float((burnt & ~earlier).sum() * KM2)}
    return out


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile, src.transform, src.crs.to_epsg()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--history", required=True, type=Path, help="folder with one subfolder per year, each written by pull_firms.py")
    p.add_argument("--layers", required=True, type=Path, help="folder with fire_days_<site>.tif and peat_peatmap_<site>.tif")
    a = p.parse_args(argv)

    years = sorted(d for d in a.history.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 4)
    if not years:
        raise SystemExit(f"no year folders (like {a.history / '2015'}) in {a.history}")
    fire_file, peat_file = a.layers / f"fire_days_{a.site}.tif", a.layers / f"peat_peatmap_{a.site}.tif"
    for f in (fire_file, peat_file):
        if not f.exists():
            raise SystemExit(f"{f} is not there yet")
    fire_now, profile, T, epsg = read(fire_file)
    peat = read(peat_file)[0] == 1
    if peat.shape != fire_now.shape:
        raise SystemExit(f"{peat_file.name} is not on the grid of {fire_file.name}")
    now = np.nan_to_num(fire_now) > 0

    count = np.zeros(now.shape, "float32")
    for folder in years:
        burnt, n = season(folder, T, epsg, now.shape)
        count += burnt
        line = f"{a.site} {folder.name}: {n} detections"
        for zone, mask in zip(ZONES, (peat, ~peat)):
            share = float((burnt & mask).sum() / max(mask.sum(), 1))
            put(f"fire_share_{zone}_{folder.name}_{a.site}", share, "share of zone", a.site, ME,
                note=f"inside the footprint of a fire detection in the {folder.name} files pulled")
            line += f", {zone.replace('_', ' ')} {share:.0%}"
        print(line)

    names = ", ".join(f.name for f in years)
    with rasterio.open(a.layers / f"fire_years_{a.site}.tif", "w", **profile) as dst:
        dst.write(count, 1)
        dst.update_tags(layer=f"earlier fire seasons ({names}) with a detection whose footprint reaches the cell", source=SOURCE)
    m = summarise(now, count > 0, peat)
    for zone in ZONES:
        z = m[zone]
        put(f"fire_earlier_share_{zone}_{a.site}", z["earlier_share"], "share of zone", a.site, ME, note=f"fire in any of {names}")
        put(f"fire_repeat_share_{zone}_{a.site}", z["repeat_share"], "share of the 2026 fire in the zone", a.site, ME,
            note=f"2026 fire on land that also had fire in any of {names}; compare with fire_earlier_share")
        put(f"fire_new_km2_{zone}_{a.site}", z["new_km2"], "km2", a.site, ME, note=f"2026 fire on land with no fire in any of {names}")
        print(f"{a.site} {zone.replace('_', ' ')}: {z['earlier_share']:.0%} had fire in {names}; of the 2026 fire there, "
              f"{z['repeat_share']:.0%} fell on such land; {z['new_km2']:.0f} km2 of 2026 fire was on land with none")


if __name__ == "__main__":
    main()
