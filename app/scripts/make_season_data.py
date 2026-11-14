# Written with Super Intelligence (SI) assistance.
"""Measured curves for the "How it was measured" panel of the season view (app/src/measure.ts).

Read from the pipeline's layers for one site and written to one small file:

    passes   every radar pass: date, track, orbit, its role in the measurement, the median change
             in HH since the dry start on peat that fell by 1 dB or more on both orbits, and the
             same on the closed reference forest
    rain     daily rain over the box, mm
    fire     mapped peat inside the footprint of a fire detection so far, km2, day by day
    dry      first and last dry day of the season, and the earliest day a start pass may fall on

The role of a pass follows pipeline/season.py and pipeline/drying/drydown.py: "before" the dry
start, a "start" pass, "between", one of the two "late" passes, or "after" the rain returned.

    python app/scripts/make_season_data.py --layers pipeline/out/layers --out app/public/season/season.json
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline"))
from season import start_passes  # noqa: E402

KM2 = 0.0025
ORBITS = {"125": "dawn", "061": "dusk"}


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def roles(dates, start_from, dry_until):
    """The part each pass of one orbit plays, in date order."""
    start = start_passes(dates, start_from)
    dry = [i for i, d in enumerate(dates) if d <= dry_until]
    late = [i for i in dry if i > max(start)][-2:]
    out = []
    for i, d in enumerate(dates):
        out.append("start" if i in start else "late" if i in late else "before" if i < min(start) else "after" if d > dry_until else "between")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--site", default="west")
    p.add_argument("--validation", type=Path, help="default: next to --layers")
    a = p.parse_args()
    L, site = a.layers, a.site
    v = json.loads((a.validation or L.parent / "validation.json").read_text())
    dry = {"first": v[f"first_dry_day_{site}"]["value"], "last": v[f"last_dry_day_{site}"]["value"], "start_from": v[f"start_passes_from_{site}"]["value"]}
    peat = read(L / f"peat_peatmap_{site}.tif") == 1
    fell = peat & np.all([read(L / f"drydown_{site}_{t}.tif") <= -1 for t in ORBITS], axis=0)
    forest = read(L / f"reference_{site}.tif") == 1

    passes = []
    for track, orbit in ORBITS.items():
        files = sorted(L.glob(f"hh_{site}_{track}_*.tif"))
        days = [f.stem.split("_")[-1] for f in files]
        for f, d, role in zip(files, days, roles(days, dry["start_from"].replace("-", ""), dry["last"].replace("-", ""))):
            change = read(f)
            passes.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "track": track, "orbit": orbit, "role": role,
                           "open": round(float(np.nanmedian(change[fell])), 2), "forest": round(float(np.nanmedian(change[forest])), 2)})
    passes.sort(key=lambda x: (x["date"], x["track"]))

    rain = json.loads((L / f"rain_daily_{site}.json").read_text())
    first = read(L / f"fire_first_day_{site}.tif")
    year = int(passes[0]["date"][:4])
    start, end = dt.date(year, 6, 10), dt.date(year, 11, 8)
    days = [start + dt.timedelta(k) for k in range((end - start).days + 1)]
    on_peat = first[peat & np.isfinite(first)]

    out = {"site": site, "sources": "NISAR L2 GCOV (ASF DAAC), NASA FIRMS, GPM IMERG (GES DISC), PEATMAP",
           "start": start.isoformat(), "end": end.isoformat(), "dry": dry,
           "fell_km2": round(float(fell.sum() * KM2)), "forest_km2": round(float(forest.sum() * KM2)),
           "passes": passes,
           "rain": [round(float(rain.get(d.isoformat(), 0.0)), 1) for d in days],
           "fire_km2": [round(float((on_peat <= d.timetuple().tm_yday).sum() * KM2), 1) for d in days]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"{site}: {len(passes)} passes, roles " + ", ".join(f"{p['date'][5:]}{p['orbit'][1]}:{p['role'][:3]}" for p in passes))
    print(f"fell on {out['fell_km2']} km2, forest {out['forest_km2']} km2, fire on peat {out['fire_km2'][-1]} km2 by {end}; wrote {a.out}")


if __name__ == "__main__":
    main()
