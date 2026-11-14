# Written with Super Intelligence (SI) assistance.
"""The time-series file behind the app's click chart (docs/DATA_CONTRACT.md section 4).

For one site: HH and HV of every pass of every track, with the scene-wide shift removed and
averaged over 250 m, resampled onto a grid that is regular in longitude and latitude and
packed as one byte per cell. The app can then look a place up with plain arithmetic.

Writes series_<site>.json and series_<site>.bin.

    python pipeline/drying/series.py --site west --tracks 125 061 --stacks pipeline/out/stacks \\
        --layers pipeline/out/layers --out pipeline/out/series
"""
import argparse
import json
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from common import block_mean, load_stack
from drydown import normalised

CELL_DEG = 0.0025     # about 277 m at this latitude
SCALE, OFFSET = 0.12, -30.0   # decibels = byte * SCALE + OFFSET; byte 0 means no data
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--tracks", nargs="+", required=True)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path, help="folder with baseline_<track>.json")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    west, south, east, north = SITES[a.site]["bbox"]
    rows, cols = round((north - south) / CELL_DEG), round((east - west) / CELL_DEG)
    grid = from_origin(west, north, CELL_DEG, CELL_DEG)

    bands, images = [], []
    for track in a.tracks:
        stack = load_stack(a.stacks / f"{a.site}_{track}.npz")
        base = json.loads((a.layers / f"baseline_{track}.json").read_text())
        for pol in ("hh", "hv"):
            for date, layer in zip(stack["dates"], normalised(stack, base, pol)):
                out = np.full((rows, cols), np.nan, "float32")
                reproject(block_mean(layer), out, src_transform=stack["T"], src_crs=f"EPSG:{stack['epsg']}", src_nodata=np.nan,
                          dst_transform=grid, dst_crs="EPSG:4326", dst_nodata=np.nan, resampling=Resampling.bilinear)
                byte = np.clip(np.round((out - OFFSET) / SCALE), 1, 255)
                images.append(np.where(np.isfinite(out), byte, 0).astype("uint8"))
                bands.append({"track": track, "pol": pol, "date": f"{date[:4]}-{date[4:6]}-{date[6:]}"})
    header = {"site": a.site, "bounds": [west, south, east, north], "cell_deg": CELL_DEG, "rows": rows, "cols": cols,
              "scale": SCALE, "offset": OFFSET, "nodata": 0, "bands": bands}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"series_{a.site}.json").write_text(json.dumps(header) + "\n")
    np.array(images).tofile(a.out / f"series_{a.site}.bin")
    cube = np.array(images)
    print(f"{a.site}: {len(bands)} bands of {rows} x {cols}, {cube.nbytes / 1e6:.1f} MB, {100 * (cube > 0).mean():.0f}% of cells have data")


if __name__ == "__main__":
    main()
