# Written with Super Intelligence (SI) assistance.
"""Download NASA FIRMS active-fire detections for one site and a range of days.

Sources: VIIRS on S-NPP, NOAA-20 and NOAA-21, and MODIS. For each, the standard product is
used for the days it covers and the near-real-time product for the days after. Which days
each product covers is read from the FIRMS service itself.

Needs a free FIRMS map key in the environment variable FIRMS_MAP_KEY
(get one at https://firms.modaps.eosdis.nasa.gov/api/map_key). The key is never written to
any file or printed.

Writes one CSV per source to <out>/firms_<source>.csv and prints the counts.

    FIRMS_MAP_KEY=... python pipeline/context/pull_firms.py --site west --start 2026-05-01 --out data/firms/west
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import time
from pathlib import Path

import certifi
import requests

API = "https://firms.modaps.eosdis.nasa.gov/api"
SENSORS = ("VIIRS_SNPP", "VIIRS_NOAA20", "VIIRS_NOAA21", "MODIS")
DAYS_PER_CALL = 5     # the area service returns at most 5 days per request
MARGIN_DEG = 0.02     # a fire just outside the box still lies within 200 m of cells inside it
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())


def fetch(url, key):
    """One request, retried. The key is removed from any error text."""
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=90, verify=certifi.where())
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    raise RuntimeError("FIRMS did not answer: " + url.replace(key, "<key>"))


def availability(key):
    """First and last day of every FIRMS product, as {name: (first, last)}."""
    rows = csv.DictReader(io.StringIO(fetch(f"{API}/data_availability/csv/{key}/ALL", key)))
    return {r["data_id"]: (dt.date.fromisoformat(r["min_date"]), dt.date.fromisoformat(r["max_date"])) for r in rows}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", help="YYYY-MM-DD, default: the last day the service has")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        raise SystemExit("set FIRMS_MAP_KEY to your FIRMS map key")
    west, south, east, north = SITES[a.site]["bbox"]
    box = f"{west - MARGIN_DEG},{south - MARGIN_DEG},{east + MARGIN_DEG},{north + MARGIN_DEG}"
    start = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end) if a.end else None
    have = availability(key)
    a.out.mkdir(parents=True, exist_ok=True)
    for sensor in SENSORS:
        header, rows = None, []
        for product in (f"{sensor}_SP", f"{sensor}_NRT"):      # standard first, then near-real-time
            if product not in have:
                continue
            first, last = have[product]
            day, stop = max(start, first), min(end or last, last)
            while day <= stop:
                n = min(DAYS_PER_CALL, (stop - day).days + 1)
                text = fetch(f"{API}/area/csv/{key}/{product}/{box}/{n}/{day.isoformat()}", key)
                table = list(csv.reader(io.StringIO(text)))
                if table and table[0] and table[0][0] == "latitude":
                    header = header or table[0] + ["product"]
                    rows += [r + [product] for r in table[1:] if r]
                elif text.strip():
                    raise RuntimeError(f"unexpected reply for {product} {day}: {text[:80].replace(key, '<key>')}")
                day += dt.timedelta(days=n)
        with open(a.out / f"firms_{sensor}.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header or ["latitude", "longitude", "acq_date", "confidence", "product"])
            w.writerows(rows)
        days = sorted({r[header.index("acq_date")] for r in rows}) if rows else []
        print(f"{a.site} {sensor}: {len(rows)} detections on {len(days)} days" + (f", {days[0]} to {days[-1]}" if days else ""))


if __name__ == "__main__":
    main()
