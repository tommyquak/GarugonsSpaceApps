# Written with Super Intelligence (SI) assistance.
"""The dry season read from the rainfall record, and which radar passes count as its start.

Why this exists: an audit of the first version found that the first passes of the stack came
just after rain. Measured from a wet surface, the "fall" was partly the surface drying off
after a shower, not a season of drying. The start is now chosen by a rule, like the end.

The rules, all read from daily rainfall (pipeline/context/rain.py):

  driest stretch   the 30 consecutive days with the least rain
  first dry day    the day after the last day of 5 mm or more before the driest stretch
  last dry day     the day before the first day of 5 mm or more, after the driest stretch,
                   that opens a 5-day window of 25 mm or more
  start passes     the first pass at least 7 days after the first dry day began, and the next
                   pass too if it comes within 14 days of that one
  late passes      the last two passes on or before the last dry day

The thresholds (5 mm, 25 mm, 7 days, 14 days) are choices, made on 14 Nov 2026 after the
audit and not tuned to a result. docs/LIMITS.md shows what moves when they move.

    python pipeline/season.py --rain pipeline/out/layers/rain_daily_west.json
        prints START_FROM=YYYYMMDD and DRY_UNTIL=YYYYMMDD for the shell, and writes both to validation.json
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

WET_DAY_MM = 5.0
WINDOW_DAYS, WINDOW_MM = 5, 25.0
SETTLE_DAYS = 7
PAIR_DAYS = 14


def dry_season(rain):
    """First and last dry day of the season, as ISO dates, from { "YYYY-MM-DD": mm }."""
    days = sorted(rain)
    mm = np.array([rain[d] for d in days])
    if len(days) < 60:
        raise ValueError("need at least 60 days of rain to find the dry season")
    i0 = int(np.argmin(np.convolve(mm, np.ones(30), "valid")))        # first day of the driest 30
    wet_before = [i for i in range(i0) if mm[i] >= WET_DAY_MM]
    first_dry = days[wet_before[-1] + 1] if wet_before else days[0]
    last_dry = days[-1]
    for i in range(i0 + 30, len(days) - WINDOW_DAYS + 1):
        if mm[i] >= WET_DAY_MM and mm[i:i + WINDOW_DAYS].sum() >= WINDOW_MM:
            last_dry = days[i - 1]
            break
    return first_dry, last_dry


def compact(iso):
    return iso.replace("-", "")


def start_passes(dates, start_from=None):
    """Indices of the start passes among `dates` (YYYYMMDD, sorted).

    With start_from: the first pass on or after it, and the next one if within PAIR_DAYS.
    Without it: the first two passes, which is what the first version did."""
    if not start_from:
        return [0, 1]
    later = [i for i, d in enumerate(dates) if d >= start_from]
    if not later:
        raise SystemExit(f"no pass on or after {start_from}")
    first = later[0]
    out = [first]
    if first + 1 < len(dates):
        a, b = (dt.date(int(d[:4]), int(d[4:6]), int(d[6:])) for d in (dates[first], dates[first + 1]))
        if (b - a).days <= PAIR_DAYS:
            out.append(first + 1)
    return out


def start_from_day(first_dry_iso):
    """The earliest day a start pass may fall on: SETTLE_DAYS after the last wet day."""
    last_wet = dt.date.fromisoformat(first_dry_iso) - dt.timedelta(1)
    return compact((last_wet + dt.timedelta(SETTLE_DAYS)).isoformat())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rain", required=True, type=Path)
    p.add_argument("--site", default=None, help="site name for the validation keys; default: taken from the file name")
    a = p.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from vjson import put
    site = a.site or a.rain.stem.replace("rain_daily_", "")
    first_dry, last_dry = dry_season(json.loads(a.rain.read_text()))
    start = start_from_day(first_dry)
    put(f"first_dry_day_{site}", first_dry, "date", site, "pipeline/season.py", note=f"day after the last day of {WET_DAY_MM:g} mm or more before the driest 30 days")
    put(f"start_passes_from_{site}", f"{start[:4]}-{start[4:6]}-{start[6:]}", "date", site, "pipeline/season.py",
        note=f"start passes are taken from this day on: {SETTLE_DAYS} days after the last wet day")
    put(f"last_dry_day_{site}", last_dry, "date", site, "pipeline/season.py",
        note=f"day before the first day of {WET_DAY_MM:g} mm or more that opens a {WINDOW_DAYS}-day window of {WINDOW_MM:g} mm or more, after the driest 30 days")
    print(f"START_FROM={start} DRY_UNTIL={compact(last_dry)}")


if __name__ == "__main__":
    main()
