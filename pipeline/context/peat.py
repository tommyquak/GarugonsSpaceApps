# Written with Super Intelligence (SI) assistance.
"""Mapped peat for one site, on the grid of the dry-down layers. For local use only.

Source: the "Indonesia Peat Lands" layer of Indonesia's Ministry of Agriculture, served by
Global Forest Watch. Its licence is not stated on the service, so the polygons and the raster
built from them stay on your machine: they are never committed and never put in a release.
The script that builds them is what the repo carries.

Writes data/peat/peat_official_<site>.geojson (the polygons as downloaded) and
<layers>/peat_official_<site>.tif (1 on mapped peat, 0 off it).

    python pipeline/context/peat.py --site west --layers pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import certifi
import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.features import rasterize

SERVICE = "https://gis-gfw.wri.org/arcgis/rest/services/country_data/asia/MapServer/10/query"
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())


def polygons(bbox):
    params = {"where": "1=1", "geometry": ",".join(str(v) for v in bbox), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
              "spatialRel": "esriSpatialRelIntersects", "outFields": "objectid", "outSR": 4326, "f": "geojson"}
    r = requests.get(SERVICE, params=params, timeout=180, verify=certifi.where())
    r.raise_for_status()
    data = r.json()
    if not data.get("features"):
        raise SystemExit("the peat service returned no polygons for this box")
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--keep", default=Path("data/peat"), type=Path, help="where the downloaded polygons are kept")
    a = p.parse_args()
    data = polygons(SITES[a.site]["bbox"])
    a.keep.mkdir(parents=True, exist_ok=True)
    (a.keep / f"peat_official_{a.site}.geojson").write_text(json.dumps(data))

    grid_file = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))[0]
    with rasterio.open(grid_file) as src:
        profile, T, epsg, shape = src.profile, src.transform, src.crs.to_epsg(), src.shape
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    shapes = []
    for feature in data["features"]:
        g = feature["geometry"]
        for poly in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            shapes.append({"type": "Polygon", "coordinates": [[tf.transform(pt[0], pt[1]) for pt in ring] for ring in poly]})
    peat = rasterize(shapes, out_shape=shape, transform=T, fill=0, dtype="uint8").astype("float32")
    with rasterio.open(a.layers / f"peat_official_{a.site}.tif", "w", **profile) as dst:
        dst.write(peat, 1)
        dst.update_tags(layer="mapped peat, official map", source="Indonesia Ministry of Agriculture via Global Forest Watch",
                        note="local use only, licence not confirmed")
    print(f"{a.site}: {len(data['features'])} polygons, {peat.sum() * 0.0025:.0f} km2 of mapped peat on the grid ({peat.mean():.0%} of it)")


if __name__ == "__main__":
    main()
