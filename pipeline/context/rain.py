# Written with Super Intelligence (SI) assistance.
"""Daily rainfall over one site from NASA GPM IMERG, and the day the dry season ended.

Reads the IMERG Late daily product (0.1 degree) through NASA's cloud OPeNDAP service, which
returns only the cells over the site, and averages them into one value per day.

The end of the dry season is read from the record with a fixed rule, so nobody picks it by
eye: after the driest 30-day stretch of the season, the rain has returned on the first day
with 5 mm or more that opens a 5-day window totalling 25 mm or more. The last dry day is
the day before. A file already downloaded is reused unless --refresh is given.

Needs a NASA Earthdata login in ~/.netrc with the application "NASA GESDISC DATA ARCHIVE"
approved. Writes rain_daily_<site>.json as { "YYYY-MM-DD": mm } (docs/DATA_CONTRACT.md
section 2) and the last dry day to validation.json.

    python pipeline/context/rain.py --site west --start 2026-05-01 --end 2026-11-12 --out pipeline/out/layers
"""
import argparse
import datetime as dt
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import certifi
import h5py
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/context/rain.py"
OPENDAP = ("https://opendap.earthdata.nasa.gov/collections/C2723754859-GES_DISC/granules/"
           "GPM_3IMERGDL.07%3A3B-DAY-L.MS.MRG.3IMERG.{day}-S000000-E235959.V07C.nc4.dap.nc4")
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())
WINDOW_DAYS, WINDOW_MM, WET_DAY_MM = 5, 25.0, 5.0


def one_day(day, lon_range, lat_range):
    """Site-mean rainfall in mm for one day, or None if the file is not there yet."""
    query = {"dap4.ce": f"/precipitation[0:0][{lon_range[0]}:{lon_range[1]}][{lat_range[0]}:{lat_range[1]}]"}
    for attempt in range(3):
        try:
            r = requests.get(OPENDAP.format(day=day.strftime("%Y%m%d")), params=query, timeout=120, verify=certifi.where())
        except requests.RequestException:
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 200 and r.content[:4] == b"\x89HDF":
            with h5py.File(io.BytesIO(r.content)) as h:
                a = h["precipitation"][:].astype("float64")
            a[a < 0] = np.nan
            return float(np.nanmean(a))
    raise RuntimeError(f"no rainfall for {day}: check the Earthdata login and the GES DISC approval")


def last_dry_day(rain):
    """Apply the rule in the module text. Returns (last dry day, first day of the rain) or (None, None)."""
    days = sorted(rain)
    mm = np.array([rain[d] for d in days])
    if len(days) < 60:
        return None, None
    month = np.convolve(mm, np.ones(30), "valid")
    driest_end = int(np.argmin(month)) + 30            # index just after the driest 30 days
    for i in range(driest_end, len(days) - WINDOW_DAYS + 1):
        if mm[i] >= WET_DAY_MM and mm[i:i + WINDOW_DAYS].sum() >= WINDOW_MM:
            return days[i - 1], days[i]
    return None, None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--refresh", action="store_true", help="download again even if the file exists")
    a = p.parse_args()
    west, south, east, north = SITES[a.site]["bbox"]
    target = a.out / f"rain_daily_{a.site}.json"
    # IMERG cells are 0.1 degree, indexed from 180 W and 90 S.
    lon_range = (int((west + 180) / 0.1), int((east + 180) / 0.1))
    lat_range = (int((south + 90) / 0.1), int((north + 90) / 0.1))
    first, last = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    days = [first + dt.timedelta(n) for n in range((last - first).days + 1)]
    if target.exists() and not a.refresh:
        rain = json.loads(target.read_text())
    else:
        with ThreadPoolExecutor(max_workers=6) as pool:
            values = list(pool.map(lambda d: one_day(d, lon_range, lat_range), days))
        rain = {d.isoformat(): round(v, 2) for d, v in zip(days, values) if v is not None}
        a.out.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(rain, indent=0) + "\n")

    dry, wet = last_dry_day(rain)
    by_month = {}
    for d, v in rain.items():
        by_month[d[:7]] = by_month.get(d[:7], 0.0) + v
    print(f"{a.site}: {len(rain)} days, {min(rain)} to {max(rain)}; mm by month: " + ", ".join(f"{m[5:]} {v:.0f}" for m, v in sorted(by_month.items())))
    if dry:
        put(f"last_dry_day_{a.site}", dry, "date", a.site, ME,
            note=f"day before the first day of {WET_DAY_MM:g} mm or more that opens a {WINDOW_DAYS}-day window of {WINDOW_MM:g} mm or more, after the driest 30 days; rain returned on {wet}")
        print(f"{a.site}: last dry day {dry}, rain returned on {wet}")
    for month, total in sorted(by_month.items()):
        put(f"rain_mm_{month}_{a.site}", float(total), "mm", a.site, ME, note="site mean, GPM IMERG Late daily")


if __name__ == "__main__":
    main()
