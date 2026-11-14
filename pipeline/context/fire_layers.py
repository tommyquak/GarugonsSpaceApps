# Written with Super Intelligence (SI) assistance.
"""Turn FIRMS detections into the fire layers the other tracks read.

Low-confidence detections are dropped (VIIRS class "l", MODIS below 30). A detection is a
point with a footprint of a few hundred metres, so each one marks every cell within 200 m.

Writes, for one site (docs/DATA_CONTRACT.md sections 2 and 4):

  fire_days_<site>.tif     on the grid of the dry-down layers: the number of distinct days
                           with a detection within 200 m. 0 where there was none.
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
from scipy.ndimage import binary_dilation

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/context/fire_layers.py"
REACH_PIXELS = 4      # 4 pixels of 50 m = 200 m
MODIS_MIN_CONFIDENCE = 30


def confident(row):
    c = row.get("confidence", "").strip().lower()
    if c in ("l", "low"):
        return False
    if c.isdigit():
        return int(c) >= MODIS_MIN_CONFIDENCE
    return True


def read_detections(folder):
    """All kept detections as (lon, lat, day), with exact duplicates removed."""
    seen = set()
    for f in sorted(Path(folder).glob("firms_*.csv")):
        with open(f, newline="") as fh:
            for row in csv.DictReader(fh):
                if "acq_date" in row and confident(row):
                    seen.add((float(row["longitude"]), float(row["latitude"]), row["acq_date"]))
    return sorted(seen, key=lambda d: d[2])


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
    for lon, lat, day in detections:
        x, y = to_grid.transform(lon, lat)
        col, row = ~T * (x, y)
        if -REACH_PIXELS <= row < shape[0] + REACH_PIXELS and -REACH_PIXELS <= col < shape[1] + REACH_PIXELS:
            by_day[day].append((int(np.clip(row, 0, shape[0] - 1)), int(np.clip(col, 0, shape[1] - 1))))
    days = np.zeros(shape, "float32")
    for day, cells in by_day.items():
        hit = np.zeros(shape, bool)
        rows, cols = zip(*cells)
        hit[rows, cols] = True
        days += binary_dilation(hit, iterations=REACH_PIXELS)
    with rasterio.open(a.layers / f"fire_days_{a.site}.tif", "w", **profile) as dst:
        dst.write(days, 1)
        dst.update_tags(layer="days with a fire detection within 200 m", source="NASA FIRMS (VIIRS and MODIS)",
                        first_day=min(by_day), last_day=max(by_day))
    burnt_km2 = float((days > 0).sum() * 0.0025)
    put(f"fire_any_km2_{a.site}", burnt_km2, "km2", a.site, ME, note=f"within 200 m of a detection, {min(by_day)} to {max(by_day)}")
    put(f"fire_detections_{a.site}", len(detections), "detections", a.site, ME, note="after dropping low-confidence ones")
    print(f"{a.site}: {len(detections)} detections on {len(by_day)} days, {min(by_day)} to {max(by_day)}; "
          f"{burnt_km2:.0f} km2 within 200 m of one; up to {int(days.max())} days at one place")

    # 2. fire_dates on the grid of the click-chart series
    if a.series and (a.series / f"series_{a.site}.json").exists():
        meta = json.loads((a.series / f"series_{a.site}.json").read_text())
        west, south, east, north = meta["bounds"]
        cell, rows, cols = meta["cell_deg"], meta["rows"], meta["cols"]
        dates = defaultdict(set)
        for lon, lat, day in detections:
            col, row = int((lon - west) // cell), int((north - lat) // cell)
            if 0 <= row < rows and 0 <= col < cols:
                dates[row * cols + col].add(day)
        out = {str(k): sorted(v) for k, v in sorted(dates.items())}
        (a.series / f"fire_dates_{a.site}.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
        print(f"{a.site}: fire dates for {len(out)} of {rows * cols} chart cells")


if __name__ == "__main__":
    main()
