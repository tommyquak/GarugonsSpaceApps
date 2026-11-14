# Written with Super Intelligence (SI) assistance.
"""Download the published daily groundwater levels near Palangka Raya and write them as plain JSON.

Two sites (pipeline/hydro/sites.json): UF, forest with little drainage, 2015 to 2018, and
DF, drained forest, 2013 to 2017. Values are metres relative to the ground surface, negative
below it. The spreadsheet is read directly as the zip of XML that it is, so no spreadsheet
library is needed. Values below -3 m are treated as missing (one such value exists and is
out of range for a water table here).

Writes <out>/gauge_daily.json as { "UF": { "YYYY-MM-DD": metres }, "DF": { ... } }.

    python pipeline/hydro/gauges.py --out pipeline/out/hydro
"""
import argparse
import datetime as dt
import io
import json
import re
import zipfile
from pathlib import Path

import certifi
import requests

CONFIG = json.loads((Path(__file__).parent / "sites.json").read_text())
LOWEST_PLAUSIBLE_M = -3.0


def read_sheet(book, number):
    """Rows of one worksheet as lists of cell text. Shared strings are looked up."""
    strings = re.findall(r"<t[^>]*>([^<]*)</t>", book.read("xl/sharedStrings.xml").decode())
    xml = book.read(f"xl/worksheets/sheet{number}.xml").decode()
    rows = []
    for row in re.findall(r"<row [^>]*>(.*?)</row>", xml, re.S):
        cells = re.findall(r'<c r="[A-Z]+\d+"([^>]*)>(?:<f>[^<]*</f>)?<v>([^<]*)</v>', row)
        rows.append([strings[int(v)] if 't="s"' in attrs else v for attrs, v in cells])
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    keep = a.out / "DailyGWL.xlsx"
    if not keep.exists():
        r = requests.get(CONFIG["download"], timeout=120, verify=certifi.where())
        r.raise_for_status()
        keep.write_bytes(r.content)
    book = zipfile.ZipFile(io.BytesIO(keep.read_bytes()))
    out = {}
    for name, site in CONFIG["sites"].items():
        series, dropped = {}, 0
        for row in read_sheet(book, site["sheet"])[1:]:          # first row is the header: Year, DOY, GWL (m)
            if len(row) < 3:
                continue
            day = dt.date(int(float(row[0])), 1, 1) + dt.timedelta(int(float(row[1])) - 1)
            level = float(row[2])
            if level < LOWEST_PLAUSIBLE_M:
                dropped += 1
                continue
            series[day.isoformat()] = round(level, 3)
        out[name] = series
        days = sorted(series)
        print(f"{name}: {len(series)} days, {days[0]} to {days[-1]}, lowest {min(series.values()):.2f} m, highest {max(series.values()):.2f} m, {dropped} implausible value(s) dropped")
    (a.out / "gauge_daily.json").write_text(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
