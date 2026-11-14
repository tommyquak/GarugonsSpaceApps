# Written with Super Intelligence (SI) assistance.
"""Peat extent for one site from PEATMAP, an openly licensed global peat map (CC BY 4.0).

PEATMAP (Xu, Morris, Liu and Holden 2018, Catena, doi 10.1016/j.catena.2017.09.010; data
doi 10.5518/252) merges the best national and regional peat maps into one. Because its
licence is open, the layer built here may be committed, released and shown in the app, with
the citation. For Indonesia it draws on the same national mapping as the official map in
peat.py, which stays local because its own licence is not stated.

Downloads the Asia archive once (27 MB) into data/peatmap/, reads the Southeast Asia
shapefile directly (no GIS library needed) and writes:

  peat_peatmap_<site>.tif       1 on mapped peat, 0 off it, on the dry-down grid
  peat_peatmap_<site>.geojson   the outline inside the site box, for the app

    python pipeline/context/peatmap.py --site west --layers pipeline/out/layers
"""
import argparse
import io
import json
import struct
import zipfile
from pathlib import Path

import certifi
import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.features import rasterize, shapes

ARCHIVE = "https://archive.researchdata.leeds.ac.uk/251/5/Asia.zip"
MEMBER = "Asia/SEA_Peatland.shp"
CEA = "+proj=cea +lon_0=0 +lat_ts=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m"   # World Cylindrical Equal Area
CITATION = "PEATMAP, Xu et al. 2018, doi 10.5518/252, CC BY 4.0"
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())


def read_rings(shp_bytes, box):
    """Rings of every polygon record whose bounding box touches `box` (x0, y0, x1, y1 in the file's units)."""
    rings, pos = [], 100                       # the file header is 100 bytes
    while pos < len(shp_bytes):
        _, words = struct.unpack(">ii", shp_bytes[pos:pos + 8])
        rec = shp_bytes[pos + 8: pos + 8 + 2 * words]
        pos += 8 + 2 * words
        if struct.unpack("<i", rec[:4])[0] not in (5, 15, 25):   # polygon, with or without heights and measures
            continue
        n_parts, n_points = struct.unpack("<ii", rec[36:44])
        parts = np.frombuffer(rec, "<i4", n_parts, 44)
        pts = np.frombuffer(rec, "<f8", 2 * n_points, 44 + 4 * n_parts).reshape(-1, 2)
        ends = np.append(parts[1:], n_points)
        for a, b in zip(parts, ends):
            ring = pts[a:b]
            if ring[:, 0].max() < box[0] or ring[:, 0].min() > box[2] or ring[:, 1].max() < box[1] or ring[:, 1].min() > box[3]:
                continue
            rings.append(ring)
    return rings


def signed_area(ring):
    x, y = ring[:, 0], ring[:, 1]
    return 0.5 * float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--keep", default=Path("data/peatmap"), type=Path, help="where the downloaded archive is kept")
    a = p.parse_args()
    archive = a.keep / "Asia.zip"
    if not archive.exists():
        a.keep.mkdir(parents=True, exist_ok=True)
        r = requests.get(ARCHIVE, timeout=600, verify=certifi.where())
        r.raise_for_status()
        archive.write_bytes(r.content)
    with zipfile.ZipFile(archive) as z:
        shp = z.read(MEMBER)

    west, south, east, north = SITES[a.site]["bbox"]
    to_cea = Transformer.from_crs(4326, CEA, always_xy=True)
    x0, y0, x1, y1 = to_cea.transform_bounds(west - 0.05, south - 0.05, east + 0.05, north + 0.05)
    rings = read_rings(shp, (x0, y0, x1, y1))

    grid_file = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))[0]
    with rasterio.open(grid_file) as src:
        profile, T, epsg, shape = src.profile, src.transform, src.crs.to_epsg(), src.shape
    to_grid = Transformer.from_crs(CEA, epsg, always_xy=True)
    outer, holes = [], []
    for ring in rings:
        xs, ys = to_grid.transform(ring[:, 0], ring[:, 1])
        geom = {"type": "Polygon", "coordinates": [list(zip(xs, ys))]}
        (outer if signed_area(ring) < 0 else holes).append(geom)   # shapefiles wind outer rings clockwise
    peat = rasterize(outer, out_shape=shape, transform=T, fill=0, dtype="uint8") if outer else np.zeros(shape, "uint8")
    if holes:
        peat[rasterize(holes, out_shape=shape, transform=T, fill=0, dtype="uint8") == 1] = 0
    with rasterio.open(a.layers / f"peat_peatmap_{a.site}.tif", "w", **profile) as dst:
        dst.write(peat.astype("float32"), 1)
        dst.update_tags(layer="mapped peat, PEATMAP", source=CITATION)

    # The outline for the app, back in longitude and latitude, simplified to the 50 m grid.
    to_lonlat = Transformer.from_crs(epsg, 4326, always_xy=True)
    features = []
    for geom, value in shapes(peat, mask=peat == 1, transform=T):
        coords = [[[round(v, 5) for v in to_lonlat.transform(x, y)] for x, y in ring] for ring in geom["coordinates"]]
        features.append({"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": coords}})
    (a.layers / f"peat_peatmap_{a.site}.geojson").write_text(json.dumps({"type": "FeatureCollection", "attribution": CITATION, "features": features}) + "\n")
    print(f"{a.site}: {len(rings)} rings near the site ({len(holes)} holes), {peat.sum() * 0.0025:.0f} km2 of mapped peat ({peat.mean():.0%} of the grid), {len(features)} outline polygons")


if __name__ == "__main__":
    main()
