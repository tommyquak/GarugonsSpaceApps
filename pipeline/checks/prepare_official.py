# Written with Super Intelligence (SI) assistance.
"""Rebuild a local official peat mask from saved Track 3 polygons, with ID checks.

The ministry layer has no stated licence. Keep source GeoJSON and output local; do not
commit or release them. The service is queried read-only to verify feature identity.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.features import rasterize

ROOT = Path(__file__).resolve().parents[2]
SITES = json.loads((ROOT / "pipeline/radar/sites.json").read_text())
SERVICE = "https://gis-gfw.wri.org/arcgis/rest/services/country_data/asia/MapServer/10/query"
SOURCE = "Indonesia Ministry of Agriculture via Global Forest Watch; MapServer layer 10"


def _query(params: dict) -> dict:
    response = requests.get(SERVICE, params={**params, "f": "json"}, timeout=60)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise ValueError(f"peat service error: {data['error']}")
    return data


def _service_features(bbox: list[float]) -> tuple[str, set[int], dict[int, int]]:
    extent = {
        "where": "1=1",
        "geometry": ",".join(map(str, bbox)),
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
    }
    oid_result = _query({**extent, "returnIdsOnly": "true"})
    oid_field = oid_result.get("objectIdFieldName")
    oids = oid_result.get("objectIds")
    count = _query({**extent, "returnCountOnly": "true"}).get("count")
    if not oid_field or not isinstance(oids, list) or count != len(oids) or len(oids) != len(set(oids)):
        raise ValueError("service feature IDs and count do not agree")
    mapping: dict[int, int] = {}
    for offset in range(0, len(oids), 100):
        batch = oids[offset:offset + 100]
        result = _query({
            "objectIds": ",".join(map(str, batch)),
            "outFields": f"{oid_field},objectid",
            "outSR": 4326,
            "returnGeometry": "false",
        })
        for feature in result.get("features", []):
            props = feature.get("attributes", feature.get("properties", {}))
            server_id = props.get(oid_field)
            source_id = props.get("objectid")
            if server_id is None or source_id is None or int(server_id) in mapping:
                raise ValueError("service did not return a unique server/source ID mapping")
            mapping[int(server_id)] = int(source_id)
    if set(mapping) != set(map(int, oids)):
        raise ValueError("fetched server IDs do not match returnIdsOnly")
    if len(set(mapping.values())) != count:
        raise ValueError("source objectid values are not unique within the query")
    return oid_field, set(map(int, oids)), mapping


def _source_ids(features: list[dict], oid_field: str, server_to_source: dict[int, int]) -> set[int]:
    ids: list[int] = []
    for feature in features:
        props = feature.get("properties") or {}
        if props.get("objectid") is not None:
            source_id = int(props["objectid"])
            if props.get(oid_field) is not None:
                server_id = int(props[oid_field])
                if server_to_source.get(server_id) != source_id:
                    raise ValueError(f"local source objectid does not match service OID {server_id}")
            ids.append(source_id)
        elif props.get(oid_field) is not None:
            oid = int(props[oid_field])
            if oid not in server_to_source:
                raise ValueError(f"local server OID {oid} is absent from the verified service response")
            ids.append(server_to_source[oid])
        else:
            raise ValueError("GeoJSON needs source objectid or the service OID field")
    if len(ids) != len(set(ids)):
        raise ValueError("local GeoJSON contains duplicate source IDs")
    return set(ids)


def _coverage_mask(shape: tuple[int, int], transform, crs, bbox: list[float]) -> np.ndarray:
    rows, cols = np.indices(shape)
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
    lons, lats = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(xs, ys)
    xmin, ymin, xmax, ymax = bbox
    lons = np.asarray(lons).reshape(shape)
    lats = np.asarray(lats).reshape(shape)
    return (lons >= xmin) & (lons <= xmax) & (lats >= ymin) & (lats <= ymax)


def prepare(site: str, layers: Path, geojson: Path, output: Path) -> dict:
    bbox = SITES[site]["bbox"]
    data = json.loads(geojson.read_text())
    features = data.get("features", [])
    if not features:
        raise ValueError("local GeoJSON has no features")

    # The service's objectid_1 is its row ID; the source polygon ID is objectid.
    # Verify both and map server OIDs back to source IDs for older local GeoJSON.
    oid_field, server_ids, server_to_source = _service_features(bbox)
    local_source_ids = _source_ids(features, oid_field, server_to_source)
    if local_source_ids != set(server_to_source.values()):
        raise ValueError("local source objectid set does not match the service query")

    grids = sorted(layers.glob(f"drydown_{site}_*.tif"))
    peat_path = layers / f"peat_official_{site}.tif"
    if not grids or not peat_path.is_file():
        raise FileNotFoundError(f"--layers must contain drydown_{site}_*.tif and {peat_path.name}")
    with rasterio.open(grids[0]) as grid, rasterio.open(peat_path) as original:
        for grid_file in grids[1:]:
            with rasterio.open(grid_file) as other:
                if other.crs != grid.crs or other.transform != grid.transform or other.shape != grid.shape:
                    raise ValueError("dry-down grids in --layers are not aligned")
        if original.crs != grid.crs or original.transform != grid.transform or original.shape != grid.shape:
            raise ValueError("local peat mask and dry-down grid are not aligned")
        original_values = original.read(1, masked=True)
        original_known = ~np.ma.getmaskarray(original_values) & np.isfinite(original_values.data)
        original_nodata = original.nodata
        if not np.isin(original_values.data[original_known], [0, 1]).all():
            raise ValueError("local official mask has classes other than 0 and 1")
        profile, transform, crs, shape = grid.profile.copy(), grid.transform, grid.crs, grid.shape

    tf = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    shapes = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            raise ValueError("local GeoJSON feature is missing geometry")
        kind = geometry["type"]
        polygons = geometry["coordinates"] if kind == "MultiPolygon" else [geometry["coordinates"]] if kind == "Polygon" else None
        if polygons is None:
            raise ValueError(f"unsupported geometry type: {kind}")
        for polygon in polygons:
            shapes.append({"type": "Polygon", "coordinates": [[tf.transform(pt[0], pt[1]) for pt in ring] for ring in polygon]})
    coverage = _coverage_mask(shape, transform, crs, bbox)
    rebuilt = rasterize(shapes, out_shape=shape, transform=transform, fill=0, dtype="uint8").astype("float32")
    known = coverage & original_known
    missing = np.nan if original_nodata is None else float(original_nodata)
    rebuilt[~known] = missing

    compare = known
    mismatches = int(np.count_nonzero(rebuilt[compare] != original_values.data[compare]))
    if mismatches:
        raise ValueError(f"rebuilt mask differs from local Track 3 mask at {mismatches} known pixels")

    profile.update(dtype="float32", count=1, nodata=missing, compress="deflate")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp.tif", dir=output.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        with rasterio.open(temp_path, "w", **profile) as dst:
            dst.write(rebuilt, 1)
            dst.update_tags(
                layer="mapped peat, official map", source=SOURCE,
                source_query_bbox_epsg4326=",".join(map(str, bbox)),
                feature_count=str(len(features)), source_objectid_count=str(len(local_source_ids)),
                server_oid_field=oid_field, service_returned_oid_count=str(len(server_ids)),
                coverage="pixel centres inside the site query bbox, and valid in the Track 3 mask; all others are nodata",
                interpretation="1=mapped peat; 0=no mapped peat polygon in query; nodata=outside query or nodata in input mask",
                licence="not stated by service; local use only",
                compared_to_local_mask=str(peat_path),
            )
        os.replace(temp_path, output)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    return {
        "site": site, "features": len(features), "service_oids": len(server_ids),
        "source_ids": len(local_source_ids), "known_bbox_pixels": int(known.sum()),
        "unknown_pixels": int((~known).sum()), "outside_query_pixels": int((~coverage).sum()),
        "input_nodata_within_query_pixels": int((coverage & ~original_known).sum()),
        "peat_pixels": int(np.count_nonzero(rebuilt == 1)),
        "no_polygon_pixels": int(np.count_nonzero(rebuilt == 0)), "matched_pixels": int(compare.sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=sorted(SITES))
    parser.add_argument("--layers", required=True, type=Path)
    parser.add_argument("--geojson", required=True, type=Path, help="local Track 3 GeoJSON; never downloaded here")
    parser.add_argument("--output", required=True, type=Path, help="local ignored output path")
    args = parser.parse_args()
    print(json.dumps(prepare(args.site, args.layers, args.geojson, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
