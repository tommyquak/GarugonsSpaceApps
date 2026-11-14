# Written with Super Intelligence (SI) assistance.
"""Build one radar stack (one site, one NISAR track) from the windows that pull_gcov.py wrote.

Each date's HH and HV power is averaged over 5 by 5 pixels (10 m to 50 m) to beat down
speckle, then converted to decibels. The result follows docs/DATA_CONTRACT.md section 1.

NISAR delivers each track on its own UTM zone, so two tracks over one site can sit on
different grids. Build one track first, then pass it as --like for the other: every date
is resampled onto the first track's grid, so both stacks of a site line up pixel for pixel.

    python pipeline/radar/build_stack.py --src data/gcov/west --track 125 --out pipeline/out/stacks/west_125.npz
    python pipeline/radar/build_stack.py --src data/gcov/west --track 61 --out pipeline/out/stacks/west_061.npz \
        --like pipeline/out/stacks/west_125.npz
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

LOOKS = 5          # 5 by 5 pixels of 10 m make one 50 m pixel
MIN_VALID = 13     # a 50 m pixel needs more than half of its 25 samples


def read_power(path):
    with rasterio.open(path) as src:
        a = src.read(1).astype("float32")
        a[(a == src.nodata) | (a <= 0) | ~np.isfinite(a)] = np.nan
        return a, src.transform, src.crs.to_epsg()


def multilook(a):
    """Average blocks of LOOKS by LOOKS in linear power. Averaging decibels would bias the result."""
    rows, cols = (a.shape[0] // LOOKS) * LOOKS, (a.shape[1] // LOOKS) * LOOKS
    blocks = a[:rows, :cols].reshape(rows // LOOKS, LOOKS, cols // LOOKS, LOOKS)
    n = np.isfinite(blocks).sum(axis=(1, 3))
    total = np.nansum(blocks, axis=(1, 3))
    return np.where(n >= MIN_VALID, total / np.maximum(n, 1), np.nan).astype("float32")


def regrid(a, transform, epsg, like):
    """Resample a 50 m power image onto the grid of another stack (bilinear, in linear power)."""
    out = np.full(like["cov"].shape, np.nan, "float32")
    reproject(a, out, src_transform=transform, src_crs=f"EPSG:{epsg}", src_nodata=np.nan,
              dst_transform=rasterio.Affine(*like["T"]), dst_crs=f"EPSG:{int(like['crs'])}", dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    return out


def granule_fields(name):
    """Track number and acquisition date from a GCOV granule name."""
    parts = name.split("_")
    return int(parts[5]), parts[11][:8]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", required=True, type=Path, help="folder written by pull_gcov.py")
    p.add_argument("--track", required=True, type=int)
    p.add_argument("--out", required=True, type=Path, help="<site>_<track>.npz")
    p.add_argument("--like", type=Path, help="a stack of the same site whose grid this one should match")
    a = p.parse_args()
    like = np.load(a.like, allow_pickle=True) if a.like else None

    by_date = {}
    for gdir in sorted(d for d in a.src.iterdir() if d.is_dir() and "_GCOV_" in d.name):
        track, date = granule_fields(gdir.name)
        hh, hv = list(gdir.glob("*_gamma0_hh.tif")), list(gdir.glob("*_gamma0_hv.tif"))
        if track != a.track or not hh or not hv:   # other tracks, and single-polarisation passes
            continue
        if date in by_date:
            raise SystemExit(f"two granules on {date} for track {a.track}: mosaic them first")
        by_date[date] = (gdir.name, hh[0], hv[0])
    if not by_date:
        raise SystemExit(f"no dual-polarisation granules for track {a.track} in {a.src}")

    dates, granules, HH, HV, grid = [], [], [], [], None
    for date in sorted(by_date):
        name, f_hh, f_hv = by_date[date]
        hh, transform, epsg = read_power(f_hh)
        hv, _, _ = read_power(f_hv)
        this_grid = (hh.shape, tuple(transform)[:6], epsg)
        if grid is None:
            grid = this_grid
        elif this_grid != grid:
            print(f"skipped {date}: its grid differs from the first date")
            continue
        hh, hv = multilook(hh), multilook(hv)
        if like is not None:
            t50 = transform * rasterio.Affine.scale(LOOKS, LOOKS)
            hh, hv = regrid(hh, t50, epsg, like), regrid(hv, t50, epsg, like)
        HH.append(hh); HV.append(hv); dates.append(date); granules.append(name)

    with np.errstate(divide="ignore", invalid="ignore"):
        hh_db = 10 * np.log10(np.array(HH))
        hv_db = 10 * np.log10(np.array(HV))
    cov = np.isfinite(hh_db).all(axis=0) & np.isfinite(hv_db).all(axis=0)
    if like is not None:
        T, out_epsg = rasterio.Affine(*like["T"]), int(like["crs"])
    else:
        T, out_epsg = rasterio.Affine(*grid[1]) * rasterio.Affine.scale(LOOKS, LOOKS), grid[2]

    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.out, hh=hh_db.astype("float32"), hv=hv_db.astype("float32"), cov=cov,
                        T=np.array(tuple(T)[:6]), crs=out_epsg, dates=np.array(dates))
    rows, cols = cov.shape
    summary = {"file": a.out.name, "track": a.track, "dates": dates, "granules": granules, "shape": [len(dates), rows, cols],
               "pixel_m": abs(T.a), "crs": f"EPSG:{out_epsg}", "native_crs": f"EPSG:{grid[2]}",
               "regridded_to": a.like.name if a.like else None, "transform": list(tuple(T)[:6]),
               "share_with_data_on_every_date": round(float(cov.mean()), 4),
               "median_hh_db": round(float(np.nanmedian(hh_db)), 2), "median_hv_db": round(float(np.nanmedian(hv_db)), 2)}
    a.out.with_suffix(".json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
