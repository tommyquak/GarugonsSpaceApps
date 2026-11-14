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

  fire_first_day_<site>.tif  the day of the year of the first detection whose footprint reaches
                           the cell, NaN where there was none. "Fire up to a date" is then
                           first day <= that date, which is how the app's season slider
                           shows the fire building up.

With --dry-until (the last dry day, from pipeline/season.py), also:

  fire_before_rain_<site>.tif      as fire_days, counting only days on or before the last dry
                                   day. Fire detected after the rain returned cannot explain
                                   what the radar saw on the pass after the rain, so this is the
                                   layer to use when comparing burnt and unburnt land after it.
  fire_before_rain_1km_<site>.tif  the same, widened to 1 km.

    python pipeline/context/fire_layers.py --site west --firms data/firms/west \\
        --layers pipeline/out/layers --series pipeline/out/series --dry-until 20261025
"""
import argparse
import csv
import datetime as dt
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
SOURCE = "NASA FIRMS (VIIRS and MODIS), active fire, not burnt area"
PIXEL_M = 50
KM2 = (PIXEL_M / 1000) ** 2
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


def compact(day):
    return day.replace("-", "")


def count_days(by_day, shape, edge, until=None):
    """Days with a detection whose footprint reaches each cell, and the same with every detection
    widened to 1 km. With `until` (YYYYMMDD), only the days on or before it count."""
    days, days_wide = np.zeros(shape, "float32"), np.zeros(shape, "float32")
    for day, items in by_day.items():
        if until and compact(day) > until:
            continue
        cells = [c for c, _ in items]
        days += stamp(shape, cells, [r for _, r in items])
        days_wide += stamp(shape, cells, [edge] * len(cells))
    return days, days_wide


def on_grid(detections, T, epsg, shape):
    """Detections grouped by day as { day: [((row, col), reach in cells), ...] } on the grid of T, keeping
    those within 1 km of it, since a detection just outside can still reach cells inside."""
    to_grid = Transformer.from_crs(4326, epsg, always_xy=True)
    by_day = defaultdict(list)
    edge = WIDE_REACH_M // PIXEL_M
    for lon, lat, day, reach in detections:
        x, y = to_grid.transform(lon, lat)
        col, row = ~T * (x, y)
        if -edge <= row < shape[0] + edge and -edge <= col < shape[1] + edge:
            by_day[day].append(((int(np.floor(row)), int(np.floor(col))), int(round(reach / PIXEL_M))))
    return by_day


def first_day(by_day, shape):
    """Day of the year of the first detection whose footprint reaches each cell; NaN where none does."""
    first = np.full(shape, np.nan, "float32")
    for day in sorted(by_day):
        reached = stamp(shape, [c for c, _ in by_day[day]], [r for _, r in by_day[day]])
        first[reached & np.isnan(first)] = dt.date.fromisoformat(day).timetuple().tm_yday
    return first


def write_layer(path, layer, profile, text, first_day, last_day):
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(layer, 1)
        dst.update_tags(layer=text, source=SOURCE, first_day=first_day, last_day=last_day)


def yyyymmdd(text):
    try:
        dt.datetime.strptime(text, "%Y%m%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYYMMDD, got {text!r}")
    return text


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--firms", required=True, type=Path, help="folder written by pull_firms.py")
    p.add_argument("--layers", required=True, type=Path, help="folder with the dry-down layers; fire_days is written here")
    p.add_argument("--series", type=Path, help="folder with series_<site>.json; fire_dates is written here")
    p.add_argument("--dry-until", type=yyyymmdd, help="last dry day, YYYYMMDD; also writes fire_before_rain_<site>.tif")
    a = p.parse_args(argv)
    detections = read_detections(a.firms)
    if not detections:
        raise SystemExit(f"no detections found in {a.firms}")

    # 1. fire_days on the grid of the dry-down layers
    grid_file = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))[0]
    with rasterio.open(grid_file) as src:
        profile, T, epsg, shape = src.profile, src.transform, src.crs.to_epsg(), src.shape
    by_day = on_grid(detections, T, epsg, shape)
    edge = WIDE_REACH_M // PIXEL_M
    days, days_wide = count_days(by_day, shape, edge)
    for name, layer, text in ((f"fire_days_{a.site}.tif", days, "days with a fire detection whose footprint reaches the cell"),
                              (f"fire_days_1km_{a.site}.tif", days_wide, "days with a fire detection within 1 km")):
        write_layer(a.layers / name, layer, profile, text, min(by_day), max(by_day))
    write_layer(a.layers / f"fire_first_day_{a.site}.tif", first_day(by_day, shape), profile,
                f"day of the year {min(by_day)[:4]} of the first fire detection whose footprint reaches the cell", min(by_day), max(by_day))
    km2, km2_wide = float((days > 0).sum() * KM2), float((days_wide > 0).sum() * KM2)
    put(f"fire_any_km2_{a.site}", km2, "km2", a.site, ME, note=f"within the footprint of a detection, {min(by_day)} to {max(by_day)}")
    put(f"fire_any_1km_km2_{a.site}", km2_wide, "km2", a.site, ME, note="within 1 km of a detection")
    put(f"fire_detections_{a.site}", len(detections), "detections", a.site, ME, note="after dropping low-confidence ones")
    print(f"{a.site}: {len(detections)} detections on {len(by_day)} days, {min(by_day)} to {max(by_day)}; "
          f"{km2:.0f} km2 inside a detection's footprint, {km2_wide:.0f} km2 within 1 km of one; up to {int(days.max())} days at one place")

    # 1b. The same, only up to the last dry day. Fire detected after the rain returned cannot explain
    #     the echo on the pass after the rain, so comparisons of burnt and unburnt land after it use this one.
    if a.dry_until:
        last_dry = f"{a.dry_until[:4]}-{a.dry_until[4:6]}-{a.dry_until[6:]}"
        kept = sorted(d for d in by_day if compact(d) <= a.dry_until)
        if not kept:
            raise SystemExit(f"no fire detection on or before the last dry day {last_dry}")
        before, before_wide = count_days(by_day, shape, edge, a.dry_until)
        for name, layer, text in ((f"fire_before_rain_{a.site}.tif", before, f"days up to {last_dry} with a fire detection whose footprint reaches the cell"),
                                  (f"fire_before_rain_1km_{a.site}.tif", before_wide, f"days up to {last_dry} with a fire detection within 1 km")):
            write_layer(a.layers / name, layer, profile, text, kept[0], kept[-1])
        after = sum(1 for _, _, day, _ in detections if compact(day) > a.dry_until)
        km2_before = float((before > 0).sum() * KM2)
        put(f"fire_before_rain_km2_{a.site}", km2_before, "km2", a.site, ME, note=f"within the footprint of a detection, {kept[0]} to {last_dry}, the last dry day")
        put(f"fire_detections_after_dry_{a.site}", after, "detections", a.site, ME, note=f"after the last dry day {last_dry}, left out of fire_before_rain")
        line = f"{a.site}: up to {last_dry}, {km2_before:.0f} km2 inside a detection's footprint; {after} detections came later and are left out"
        peat_file = a.layers / f"peat_peatmap_{a.site}.tif"
        if peat_file.exists():
            with rasterio.open(peat_file) as src:
                peat = src.read(1)
            if peat.shape != shape:
                raise SystemExit(f"{peat_file.name} is not on the grid of {grid_file.name}")
            for zone, mask in (("on_peat", peat == 1), ("off_peat", peat == 0)):
                burnt = mask & (before > 0)
                put(f"fire_before_rain_km2_{zone}_{a.site}", float(burnt.sum() * KM2), "km2", a.site, ME, note=f"fire detected up to {last_dry}")
                put(f"fire_before_rain_share_{zone}_{a.site}", float(burnt.sum() / max(mask.sum(), 1)), "share of zone", a.site, ME)
                line += f"; {zone.replace('_', ' ')} {burnt.sum() / max(mask.sum(), 1):.0%}"
        print(line)

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
