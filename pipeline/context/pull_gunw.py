# Written with Super Intelligence (SI) assistance.
"""Download the interferometric coherence of NISAR L2 GUNW pairs for the site boxes, without whole granules.

A GUNW granule holds one interferogram between two passes of the same track (here mostly 12
days apart) and, with it, the coherence: how alike the radar echo of each place was on the two
passes, from 0 (nothing in common) to 1 (unchanged). Fire, clearing and flooding all change the
ground between passes and pull coherence down. This script reads only the coherence layer, and
only the part over each site box, over HTTP, as pipeline/radar/pull_gcov.py does for backscatter.

Writes <out>/<site>/<granule>_coh.tif (coherence on the product's own grid) with the track and
both pass dates in its tags, and a manifest.json per site.

Needs a NASA Earthdata login in ~/.netrc (machine urs.earthdata.nasa.gov), with the Alaska
Satellite Facility authorised for it.

    python pipeline/context/pull_gunw.py --inspect                     # print the layout of one granule
    python pipeline/context/pull_gunw.py --sites west east --out data/gunw
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
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())
ROOT = "science/LSAR/GUNW/grids/frequencyA"
NODATA = -9999.0


def search(bbox, tracks):
    params = {"platform": "NISAR", "processingLevel": "GUNW", "bbox": ",".join(str(v) for v in bbox),
              "output": "jsonlite", "maxResults": 2000}
    r = requests.get(ASF_SEARCH, params=params, timeout=120)
    r.raise_for_status()
    found = sorted(r.json()["results"], key=lambda g: g["startTime"])
    return [g for g in found if int(g.get("path", -1)) in tracks]


def pair_dates(name):
    """Reference and secondary pass dates (YYYYMMDD) from a GUNW granule name."""
    parts = name.split("_")
    stamps = [p for p in parts if len(p) == 15 and p[8] == "T" and p[:8].isdigit()]
    return stamps[0][:8], stamps[2][:8]


def coherence_path(h5):
    """The HH coherence of the unwrapped interferogram, or failing that the first coherence layer found."""
    found = []
    h5[ROOT].visititems(lambda path, obj: found.append(path) if isinstance(obj, h5py.Dataset) and path.endswith("coherenceMagnitude") else None)
    if not found:
        raise KeyError("no coherenceMagnitude layer in this granule")
    found.sort(key=lambda p: ("unwrappedInterferogram" not in p, "/HH/" not in f"/{p}/", p))
    return f"{ROOT}/{found[0]}"


def grid_of(h5, layer):
    """x and y pixel-centre coordinates and EPSG code of the grid a layer sits on: the nearest group above it that has them."""
    group = h5[layer].parent
    while group.name != "/":
        if "xCoordinates" in group and "yCoordinates" in group:
            proj = group["projection"]
            epsg = int(proj[()]) if proj.shape == () else int(proj.attrs.get("epsg_code"))
            return group["xCoordinates"][:].astype("f8"), group["yCoordinates"][:].astype("f8"), epsg
        group = group.parent
    raise KeyError(f"no coordinates found above {layer}")


def window(x, y, epsg, bbox):
    """Row and column range of the grid that covers a lon/lat box. y runs north to south."""
    west, south, east, north = bbox
    x0, y0, x1, y1 = Transformer.from_crs(4326, epsg, always_xy=True).transform_bounds(west, south, east, north, densify_pts=21)
    c0, c1 = np.searchsorted(x, x0, "left"), np.searchsorted(x, x1, "right")
    r0, r1 = np.searchsorted(-y, -y1, "left"), np.searchsorted(-y, -y0, "right")
    r0, r1, c0, c1 = (int(np.clip(v, 0, n)) for v, n in ((r0, y.size), (r1, y.size), (c0, x.size), (c1, x.size)))
    if r1 <= r0 or c1 <= c0:
        raise ValueError("the box does not intersect this granule")
    return r0, r1, c0, c1


def open_granule(url, block_mb):
    # Follow the Earthdata login redirects once (credentials from ~/.netrc) to get a signed URL that allows range reads.
    r = requests.Session().get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=120)
    if r.status_code not in (200, 206):
        raise RuntimeError(f"HTTP {r.status_code}: is the Earthdata login in ~/.netrc, with ASF authorised?")
    fs = fsspec.filesystem("http", block_size=block_mb * 1024 * 1024, cache_type="blockcache")
    return fs.open(r.url, "rb")


def pull_one(granule, sites, out, block_mb):
    name = granule["granuleName"]
    targets = {s: out / s / f"{name}_coh.tif" for s in sites}
    if all(p.exists() for p in targets.values()):
        return {"granule": name, "skipped": True}
    t0 = time.time()
    ref, sec = pair_dates(name)
    with open_granule(granule["downloadUrl"], block_mb) as fo, h5py.File(fo, "r") as h5:
        layer = coherence_path(h5)
        x, y, epsg = grid_of(h5, layer)
        dx, dy = float(np.median(np.diff(x))), float(np.median(np.diff(y)))
        for site, path in targets.items():
            r0, r1, c0, c1 = window(x, y, epsg, SITES[site]["bbox"])
            data = h5[layer][r0:r1, c0:c1].astype("float32")
            data[~np.isfinite(data) | (data < 0) | (data > 1)] = NODATA
            transform = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2) * Affine.translation(c0, r0)
            path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(path, "w", driver="GTiff", dtype="float32", count=1, height=data.shape[0], width=data.shape[1],
                               crs=f"EPSG:{epsg}", transform=transform, nodata=NODATA, compress="DEFLATE", predictor=3) as dst:
                dst.write(data, 1)
                dst.update_tags(sensor="NISAR L-SAR", source_product="L2 GUNW", source_granule=name, layer=layer,
                                track_number=str(int(granule["path"])), reference_date=ref, secondary_date=sec,
                                units="coherence, 0 to 1", pixel_m=str(abs(dx)))
    return {"granule": name, "track": int(granule["path"]), "reference": ref, "secondary": sec, "layer": layer,
            "pixel_m": abs(dx), "seconds": round(time.time() - t0, 1)}


def inspect(granule, block_mb):
    with open_granule(granule["downloadUrl"], block_mb) as fo, h5py.File(fo, "r") as h5:
        print(granule["granuleName"])
        h5[ROOT].visititems(lambda path, obj: print(f"  {path}  {obj.shape} {obj.dtype}") if isinstance(obj, h5py.Dataset) else None)
        print("coherence layer chosen:", coherence_path(h5))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sites", nargs="+", default=["west", "east"], choices=sorted(SITES))
    p.add_argument("--tracks", nargs="+", type=int, default=[125, 61])
    p.add_argument("--out", type=Path, default=Path("data/gunw"))
    p.add_argument("--workers", type=int, default=4, help="signed URLs expire in about an hour, so keep this small")
    p.add_argument("--block-mb", type=int, default=2)
    p.add_argument("--inspect", action="store_true", help="print the layout of the first granule and stop")
    a = p.parse_args()
    boxes = [SITES[s]["bbox"] for s in a.sites]
    union = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    granules = search(union, a.tracks)
    print(f"{len(granules)} GUNW granules over {', '.join(a.sites)}, tracks {a.tracks}")
    if a.inspect:
        inspect(granules[0], a.block_mb)
        return
    records, failed = [], 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs = {pool.submit(pull_one, g, a.sites, a.out, a.block_mb): g["granuleName"] for g in granules}
        for job in as_completed(jobs):
            try:
                rec = job.result()
                records.append(rec)
                print("ok  ", jobs[job], "(already there)" if rec.get("skipped") else f"{rec['seconds']} s")
            except Exception as exc:  # keep going: one bad granule should not stop the pull
                failed += 1
                print("FAIL", jobs[job], repr(exc))
    for site in a.sites:
        (a.out / site).mkdir(parents=True, exist_ok=True)
        (a.out / site / "manifest.json").write_text(json.dumps(sorted(records, key=lambda r: r["granule"]), indent=1) + "\n")
    print(f"finished: {len(granules) - failed} ok, {failed} failed")


if __name__ == "__main__":
    main()
