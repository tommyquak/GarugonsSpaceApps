# Written with Super Intelligence (SI) assistance.
"""Daily rainfall over the gauge sites from NASA GPM IMERG, for the gauge years and for 2026.

The same source and the same reader as pipeline/context/rain.py, over the small box in
pipeline/hydro/sites.json. Needs a NASA Earthdata login in ~/.netrc. A day already in the
output file is not downloaded again, so the script can be stopped and restarted.

Writes <out>/rain_gauges.json as { "YYYY-MM-DD": mm }.

    python pipeline/hydro/rain_history.py --out pipeline/out/hydro --spans 2013-01-01:2018-12-31 2026-01-01:2026-11-12
"""
import argparse
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "context"))
from rain import granule_names, one_day  # noqa: E402

CONFIG = json.loads((Path(__file__).parent / "sites.json").read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--spans", nargs="+", required=True, help="first:last pairs of days, YYYY-MM-DD:YYYY-MM-DD")
    a = p.parse_args()
    west, south, east, north = CONFIG["rain_box"]
    lon_range = (int((west + 180) / 0.1), int((east + 180) / 0.1))
    lat_range = (int((south + 90) / 0.1), int((north + 90) / 0.1))
    a.out.mkdir(parents=True, exist_ok=True)
    target = a.out / "rain_gauges.json"
    rain = json.loads(target.read_text()) if target.exists() else {}
    days = []
    for span in a.spans:
        first, last = (dt.date.fromisoformat(s) for s in span.split(":"))
        days += [first + dt.timedelta(n) for n in range((last - first).days + 1)]
    todo = [d for d in days if d.isoformat() not in rain]
    names = {}
    for span in a.spans:
        first, last = (dt.date.fromisoformat(s) for s in span.split(":"))
        names.update(granule_names(first, last))
    print(f"{len(days)} days asked for, {len(todo)} to download")
    for start in range(0, len(todo), 120):              # save every 120 days so a stop loses little
        chunk = todo[start:start + 120]
        with ThreadPoolExecutor(max_workers=6) as pool:
            values = list(pool.map(lambda d: one_day(d, lon_range, lat_range, names.get(d)), chunk))
        rain.update({d.isoformat(): round(v, 2) for d, v in zip(chunk, values) if v is not None})
        target.write_text(json.dumps(dict(sorted(rain.items())), indent=0) + "\n")
        print(f"  {min(start + 120, len(todo))} of {len(todo)}", flush=True)
    print(f"{len(rain)} days in {target}")


if __name__ == "__main__":
    main()
