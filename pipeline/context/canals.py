# Written with Super Intelligence (SI) assistance.
"""Canals, drains and ditches for one site from OpenStreetMap, and the distance to the nearest one.

Drained peat is peat with a canal nearby, so distance to a canal is the "human driver" layer.
OpenStreetMap is incomplete here: a place far from a mapped canal may still be drained.

Writes canals_osm_<site>.geojson (lines, OpenStreetMap contributors, ODbL) and
canal_distance_<site>.tif (metres to the nearest mapped canal, on the dry-down grid).

    python pipeline/context/canals.py --site west --layers pipeline/out/layers
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
from scipy.ndimage import distance_transform_edt

# Public Overpass servers, tried in turn: any one of them can be busy.
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter")
KINDS = "canal|drain|ditch"
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--layers", required=True, type=Path)
    a = p.parse_args()
    west, south, east, north = SITES[a.site]["bbox"]
    query = f'[out:json][timeout:180];way["waterway"~"^({KINDS})$"]({south},{west},{north},{east});out geom;'
    elements = None
    for server in OVERPASS:
        try:
            r = requests.post(server, data={"data": query}, timeout=240, verify=certifi.where(),
                              headers={"User-Agent": "space-apps-peat-map/1.0"})
            if r.status_code == 200:
                elements = r.json()["elements"]
                break
        except (requests.RequestException, ValueError):
            continue
    if elements is None:
        raise SystemExit("no Overpass server answered; try again in a minute")
    ways = [w for w in elements if w.get("type") == "way" and len(w.get("geometry", [])) > 1]
    features = [{"type": "Feature", "properties": {"osm_id": w["id"], "waterway": w["tags"].get("waterway")},
                 "geometry": {"type": "LineString", "coordinates": [[pt["lon"], pt["lat"]] for pt in w["geometry"]]}} for w in ways]
    out = {"type": "FeatureCollection", "features": features,
           "attribution": "OpenStreetMap contributors, ODbL, https://www.openstreetmap.org/copyright"}
    (a.layers / f"canals_osm_{a.site}.geojson").write_text(json.dumps(out) + "\n")

    grid_file = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))[0]
    with rasterio.open(grid_file) as src:
        profile, T, epsg, shape = src.profile, src.transform, src.crs.to_epsg(), src.shape
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    lines = [{"type": "LineString", "coordinates": [tf.transform(x, y) for x, y in f["geometry"]["coordinates"]]} for f in features]
    on = rasterize(lines, out_shape=shape, transform=T, fill=0, dtype="uint8", all_touched=True).astype(bool) if lines else np.zeros(shape, bool)
    distance = (distance_transform_edt(~on) * 50).astype("float32") if on.any() else np.full(shape, np.nan, "float32")
    with rasterio.open(a.layers / f"canal_distance_{a.site}.tif", "w", **profile) as dst:
        dst.write(distance, 1)
        dst.update_tags(layer="distance to the nearest mapped canal", units="m", source="OpenStreetMap contributors")
    km = sum(len(f["geometry"]["coordinates"]) for f in features)
    print(f"{a.site}: {len(features)} canals, drains and ditches ({km} points); {100 * (distance < 1000).mean():.0f}% of the site within 1 km of one")


if __name__ == "__main__":
    main()
