# Written with Super Intelligence (SI) assistance.
"""Step 4 of drying: the one-look map.

Colour: how far HH fell (mean of the two orbits) where a block dried beyond the noise
floor on both orbits. Grey: everything else, shaded by season-mean HH so rivers and
forest edges stay readable. Optional: the peat boundary as a line, with land outside it
faded, so the eye goes to drying on peat.

    python pipeline/drying/one_look_map.py --layers pipeline/out/layers --stacks pipeline/out/stacks \\
        --sites west east --tracks 125 061 --out pipeline/out/one_look_map.png [--peat peat.geojson]
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer
from rasterio.features import rasterize

RAMP = LinearSegmentedColormap.from_list("dry", ["#f6e27a", "#f0a04b", "#d9502e", "#8f1d1d", "#4a0d12"])
FULL_SCALE_DB = 3.0


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.crs.to_epsg()


def peat_shapes(path, epsg):
    """Polygons of a GeoJSON file (lon/lat) as geometries in the map's projection."""
    tf = Transformer.from_crs(4326, epsg, always_xy=True)
    out = []
    for feature in json.loads(Path(path).read_text())["features"]:
        g = feature["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            out.append({"type": "Polygon", "coordinates": [[tf.transform(pt[0], pt[1]) for pt in ring] for ring in poly]})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--sites", nargs="+", required=True)
    p.add_argument("--tracks", nargs=2, required=True)
    p.add_argument("--peat", type=Path, help="peat boundary polygons, GeoJSON in lon/lat")
    p.add_argument("--min-db", type=float, default=0.0, help="only colour blocks that fell by at least this much")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()

    fig, ax = plt.subplots(figsize=(13, 8.2), dpi=150)
    fig.patch.set_facecolor("#111418"); ax.set_facecolor("#111418")
    stats = {}
    for site in a.sites:
        dried, T, epsg = read(a.layers / f"dried_{site}.tif")
        fall = -np.mean([read(a.layers / f"drydown_{site}_{t}.tif")[0] for t in a.tracks], axis=0)
        back = np.nanmean(np.load(a.stacks / f"{site}_{a.tracks[0]}.npz")["hh"], axis=0)
        rows, cols = dried.shape
        extent = (T.c, T.c + T.a * cols, T.f + T.e * rows, T.f)
        show = (dried == 1) & (fall >= a.min_db)
        peat = None
        if a.peat:
            shapes = peat_shapes(a.peat, epsg)
            peat = rasterize(shapes, out_shape=dried.shape, transform=T, fill=0, dtype="uint8").astype(bool)
        grey = plt.cm.gray(Normalize(-14, -3)(back))
        grey[..., :3] *= 0.55
        rgba = grey.copy()
        colour = RAMP(Normalize(0, FULL_SCALE_DB, clip=True)(fall))
        rgba[show] = colour[show]
        if peat is not None:   # fade what is outside mapped peat
            off = show & ~peat
            rgba[off, :3] = 0.25 * colour[off, :3] + 0.75 * grey[off, :3]
        rgba[~np.isfinite(dried)] = (0, 0, 0, 0)
        ax.imshow(rgba, extent=extent, interpolation="nearest", zorder=1 if site == a.sites[0] else 2)
        if peat is not None:
            ax.contour(np.linspace(extent[0], extent[1], cols), np.linspace(extent[3], extent[2], rows), peat.astype(float),
                       levels=[0.5], colors="white", linewidths=0.5, alpha=0.8, zorder=5)
            v = np.isfinite(dried)
            stats[site] = {"peat_km2": float((v & peat).sum() * 0.0025), "shown_on_peat_km2": float((show & peat).sum() * 0.0025),
                           "shown_off_peat_km2": float((show & ~peat).sum() * 0.0025), "off_peat_km2": float((v & ~peat).sum() * 0.0025)}
    ax.set_aspect("equal"); ax.axis("off")
    sm = plt.cm.ScalarMappable(norm=Normalize(0, FULL_SCALE_DB), cmap=RAMP)
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("Fall in HH brightness over the dry season (dB)", color="white")
    cb.ax.yaxis.set_tick_params(color="white"); plt.setp(cb.ax.get_yticklabels(), color="white")
    title = "Where the land dried, June to October 2026"
    if a.min_db:
        title += f" (blocks that fell by {a.min_db:g} dB or more)"
    ax.set_title(title, color="white", fontsize=15, loc="left")
    fig.savefig(a.out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
