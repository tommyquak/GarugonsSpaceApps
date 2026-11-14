# Written with Super Intelligence (SI) assistance.
"""Download a window of NISAR L2 GCOV backscatter for one site, without downloading whole granules.

A GCOV granule is about 2 GB, but a study box covers a small part of the frame. The
products are HDF5 files stored in compressed chunks, so this script opens each granule
over HTTP and reads only the chunks that fall inside the box.

Output: one folder per granule holding <granule>_gamma0_hh.tif, <granule>_gamma0_hv.tif
(linear gamma-nought power on the product's own 10 m grid) and manifest.json.

Needs a NASA Earthdata login in ~/.netrc (machine urs.earthdata.nasa.gov).

    python pipeline/radar/pull_gcov.py --site west --out data/gcov/west
    python pipeline/radar/pull_gcov.py --bbox 113.6 -3.2 114.3 -2.4 --tracks 125 61 --out data/gcov/west
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import fsspec  # noqa: E402
import h5py  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import requests  # noqa: E402
from pyproj import Transformer  # noqa: E402
from rasterio.transform import Affine  # noqa: E402

ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"
NODATA = -9999.0
LAYERS = {"gamma0_hh": "HHHH", "gamma0_hv": "HVHV"}
SITES = json.loads((Path(__file__).parent / "sites.json").read_text())


def search(bbox, tracks):
    """Granules over the box, oldest first, optionally limited to some track numbers."""
    params = {"platform": "NISAR", "processingLevel": "GCOV", "bbox": ",".join(str(v) for v in bbox),
              "output": "jsonlite", "maxResults": 2000}
    r = requests.get(ASF_SEARCH, params=params, timeout=120)
    r.raise_for_status()
    found = sorted(r.json()["results"], key=lambda g: g["startTime"])
    if tracks:
        found = [g for g in found if int(g.get("path", -1)) in tracks]
    return found


def window(x, y, epsg, bbox):
    """Row and column range of the product grid that covers a lon/lat box. y runs north to south."""
    west, south, east, north = bbox
    x0, y0, x1, y1 = Transformer.from_crs(4326, epsg, always_xy=True).transform_bounds(west, south, east, north, densify_pts=21)
    c0, c1 = np.searchsorted(x, x0, "left"), np.searchsorted(x, x1, "right")
    r0, r1 = np.searchsorted(-y, -y1, "left"), np.searchsorted(-y, -y0, "right")
    r0, r1 = (int(np.clip(v, 0, y.size)) for v in (r0, r1))
    c0, c1 = (int(np.clip(v, 0, x.size)) for v in (c0, c1))
    if r1 <= r0 or c1 <= c0:
        raise ValueError("the box does not intersect this granule")
    return r0, r1, c0, c1


def pull_one(granule, bbox, out_dir, block_mb, force):
    name = granule["granuleName"]
    gdir = out_dir / name
    manifest = gdir / "manifest.json"
    if manifest.exists() and not force:
        return json.loads(manifest.read_text()) | {"skipped": True}
    t0 = time.time()
    # Follow the Earthdata login redirects once to get a signed URL that allows range reads.
    r = requests.Session().get(granule["downloadUrl"], headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=120)
    if r.status_code not in (200, 206):
        raise RuntimeError(f"HTTP {r.status_code} for {name}")
    fs = fsspec.filesystem("http", block_size=block_mb * 1024 * 1024, cache_type="blockcache")
    with fs.open(r.url, "rb") as fo, h5py.File(fo, "r") as h5:
        ident = h5["science/LSAR/identification"]
        grid = h5["science/LSAR/GCOV/grids/frequencyA"]
        x = grid["xCoordinates"][:].astype("f8")
        y = grid["yCoordinates"][:].astype("f8")
        epsg = int(grid["projection"][()])
        dx, dy = float(np.median(np.diff(x))), float(np.median(np.diff(y)))
        r0, r1, c0, c1 = window(x, y, epsg, bbox)
        # Coordinates are pixel centres; a GeoTIFF transform is the top-left corner.
        transform = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2) * Affine.translation(c0, r0)
        tags = {"sensor": "NISAR L-SAR", "source_product": "L2 GCOV", "source_granule": name,
                "track_number": str(int(ident["trackNumber"][()])), "frame_number": str(int(ident["frameNumber"][()])),
                "acquisition_date": ident["zeroDopplerStartTime"][()].decode()[:10],
                "bbox_wgs84": ",".join(str(v) for v in bbox), "units": "linear gamma-nought power"}
        gdir.mkdir(parents=True, exist_ok=True)
        written, missing = {}, []
        for key, dataset in LAYERS.items():
            if dataset not in grid:  # single-polarisation granules carry no HV
                missing.append(key)
                continue
            data = grid[dataset][r0:r1, c0:c1].astype("float32")
            data[~np.isfinite(data)] = NODATA
            path = gdir / f"{name}_{key}.tif"
            with rasterio.open(path, "w", driver="GTiff", dtype="float32", count=1, height=data.shape[0], width=data.shape[1],
                               crs=f"EPSG:{epsg}", transform=transform, nodata=NODATA, tiled=True, blockxsize=256,
                               blockysize=256, compress="DEFLATE", predictor=3) as dst:
                dst.write(data, 1)
                dst.update_tags(**tags, layer=key)
            written[key] = path.name
    record = {"granule": name, "outputs": written, "missing_layers": missing, "tags": tags, "seconds": round(time.time() - t0, 1)}
    manifest.write_text(json.dumps(record, indent=2))
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", choices=sorted(SITES), help="a site from sites.json")
    p.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    p.add_argument("--tracks", nargs="+", type=int, help="NISAR track numbers to keep")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--workers", type=int, default=4, help="signed URLs expire in about an hour, so keep this small")
    p.add_argument("--block-mb", type=int, default=2)
    p.add_argument("--limit", type=int, help="only the first N granules, for a quick test")
    p.add_argument("--force", action="store_true", help="download again even if a manifest exists")
    a = p.parse_args()
    if not (a.site or a.bbox):
        p.error("give --site or --bbox")
    bbox = tuple(a.bbox) if a.bbox else tuple(SITES[a.site]["bbox"])
    tracks = a.tracks or (SITES[a.site]["tracks"] if a.site else None)
    granules = search(bbox, tracks)[: a.limit]
    print(f"{len(granules)} GCOV granules over {bbox}, tracks {tracks or 'all'}")
    a.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs = {pool.submit(pull_one, g, bbox, a.out, a.block_mb, a.force): g["granuleName"] for g in granules}
        for job in as_completed(jobs):
            try:
                rec = job.result()
                print("ok  ", jobs[job], "(already there)" if rec.get("skipped") else f"{rec['seconds']} s")
            except Exception as exc:  # keep going: one bad granule should not stop the pull
                failed += 1
                print("FAIL", jobs[job], repr(exc))
    print(f"finished: {len(granules) - failed} ok, {failed} failed")


if __name__ == "__main__":
    main()
