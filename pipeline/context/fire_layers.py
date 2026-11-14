# Written with Super Intelligence (SI) assistance.
"""Turn FIRMS detections into the fire layers the other tracks read.

Low-confidence detections are dropped (VIIRS class "l", MODIS below 30). A detection is not
a point: it is a pixel whose size is given with it (the scan and track columns), about
0.4 km for VIIRS and 1 km or more for MODIS. Each detection therefore marks every cell
within half its pixel size, never less than 200 m and never more than 1 km. A second layer
marks everything within 1 km of any detection, for the cautious reading of "no fire nearby".

These are active-fire detections, not burnt area. Fire under thick smoke or cloud, and
low smouldering fire in peat, can be missed.

Writes, for one site (docs/DATA_CONTRACT.md sections 2 and 4):

  fire_days_<site>.tif     on the grid of the dry-down layers: the number of distinct days
                           with a detection whose footprint reaches the cell. 0 where none.
  fire_days_1km_<site>.tif the same with every detection widened to 1 km.
  fire_dates_<site>.json   on the grid of series_<site>.json: for each cell that had a
                           detection, the list of days, as { "<row * cols + col>": [...] }.

    python pipeline/context/fire_layers.py --site west --firms data/firms/west \\
        --layers pipeline/out/layers --series pipeline/out/series
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/context/fire_layers.py"
PIXEL_M = 50
MIN_REACH_M, MAX_REACH_M, WIDE_REACH_M = 200, 1000, 1000
MODIS_MIN_CONFIDENCE = 30


def confident(row):
    c = row.get("confidence", "").strip().lower()
    if c in ("l", "low"):
        return False
    if c.isdigit():
        return int(c) >= MODIS_MIN_CONFIDENCE
    return True


def reach_m(row):
    """Half the detection's pixel size in metres, kept between the smallest and largest reach."""
    try:
        size_km = max(float(row.get("scan") or 0), float(row.get("track") or 0))
    except ValueError:
        size_km = 0.0
    return float(np.clip(size_km * 1000 / 2, MIN_REACH_M, MAX_REACH_M))


def read_detections(folder):
    """All kept detections as (lon, lat, day, reach in metres), with exact duplicates removed."""
    seen = {}
    for f in sorted(Path(folder).glob("firms_*.csv")):
        with open(f, newline="") as fh:
            for row in csv.DictReader(fh):
                if "acq_date" in row and confident(row):
                    key = (float(row["longitude"]), float(row["latitude"]), row["acq_date"])
                    seen[key] = max(seen.get(key, 0.0), reach_m(row))
    return sorted(((lon, lat, day, r) for (lon, lat, day), r in seen.items()), key=lambda d: d[2])


def disk(radius_px):
    y, x = np.ogrid[-radius_px:radius_px + 1, -radius_px:radius_px + 1]
    return (x * x + y * y) <= radius_px * radius_px


def stamp(shape, cells, radii_px):
    """A mask with a filled circle of its own radius around every cell."""
    out = np.zeros(shape, bool)
    disks = {}
    for (row, col), r in zip(cells, radii_px):
        d = disks.setdefault(r, disk(r))
        r0, r1, c0, c1 = max(row - r, 0), min(row + r + 1, shape[0]), max(col - r, 0), min(col + r + 1, shape[1])
        if r0 >= r1 or c0 >= c1:
            continue
        out[r0:r1, c0:c1] |= d[r0 - (row - r):r1 - (row - r), c0 - (col - r):c1 - (col - r)]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--firms", required=True, type=Path, help="folder written by pull_firms.py")
    p.add_argument("--layers", required=True, type=Path, help="folder with the dry-down layers; fire_days is written here")
    p.add_argument("--series", type=Path, help="folder with series_<site>.json; fire_dates is written here")
    a = p.parse_args()
    detections = read_detections(a.firms)
    if not detections:
        raise SystemExit(f"no detections found in {a.firms}")

    # 1. fire_days on the grid of the dry-down layers
    grid_file = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))[0]
    with rasterio.open(grid_file) as src:
        profile, T, epsg, shape = src.profile, src.transform, src.crs.to_epsg(), src.shape
    to_grid = Transformer.from_crs(4326, epsg, always_xy=True)
    by_day = defaultdict(list)
    edge = WIDE_REACH_M // PIXEL_M
    for lon, lat, day, reach in detections:
        x, y = to_grid.transform(lon, lat)
        col, row = ~T * (x, y)
        if -edge <= row < shape[0] + edge and -edge <= col < shape[1] + edge:
            by_day[day].append(((int(np.floor(row)), int(np.floor(col))), int(round(reach / PIXEL_M))))
    days, days_wide = np.zeros(shape, "float32"), np.zeros(shape, "float32")
    for day, items in by_day.items():
        cells = [c for c, _ in items]
        days += stamp(shape, cells, [r for _, r in items])
        days_wide += stamp(shape, cells, [edge] * len(cells))
    for name, layer, text in ((f"fire_days_{a.site}.tif", days, "days with a fire detection whose footprint reaches the cell"),
                              (f"fire_days_1km_{a.site}.tif", days_wide, "days with a fire detection within 1 km")):
        with rasterio.open(a.layers / name, "w", **profile) as dst:
            dst.write(layer, 1)
            dst.update_tags(layer=text, source="NASA FIRMS (VIIRS and MODIS), active fire, not burnt area",
                            first_day=min(by_day), last_day=max(by_day))
    km2, km2_wide = float((days > 0).sum() * 0.0025), float((days_wide > 0).sum() * 0.0025)
    put(f"fire_any_km2_{a.site}", km2, "km2", a.site, ME, note=f"within the footprint of a detection, {min(by_day)} to {max(by_day)}")
    put(f"fire_any_1km_km2_{a.site}", km2_wide, "km2", a.site, ME, note="within 1 km of a detection")
    put(f"fire_detections_{a.site}", len(detections), "detections", a.site, ME, note="after dropping low-confidence ones")
    print(f"{a.site}: {len(detections)} detections on {len(by_day)} days, {min(by_day)} to {max(by_day)}; "
          f"{km2:.0f} km2 inside a detection's footprint, {km2_wide:.0f} km2 within 1 km of one; up to {int(days.max())} days at one place")

    # 2. fire_dates on the grid of the click-chart series
    if a.series and (a.series / f"series_{a.site}.json").exists():
        meta = json.loads((a.series / f"series_{a.site}.json").read_text())
        west, south, east, north = meta["bounds"]
        cell, rows, cols = meta["cell_deg"], meta["rows"], meta["cols"]
        dates = defaultdict(set)
        for lon, lat, day, _ in detections:
            col, row = int((lon - west) // cell), int((north - lat) // cell)
            if 0 <= row < rows and 0 <= col < cols:
                dates[row * cols + col].add(day)
        out = {str(k): sorted(v) for k, v in sorted(dates.items())}
        (a.series / f"fire_dates_{a.site}.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
        print(f"{a.site}: fire dates for {len(out)} of {rows * cols} chart cells")


if __name__ == "__main__":
    main()
