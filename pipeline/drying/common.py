# Written with Super Intelligence (SI) assistance.
"""Helpers shared by the drying scripts: load a stack, average over blocks, write a layer."""
from datetime import date

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import Affine
from scipy.ndimage import uniform_filter

BLOCK = 5   # 5 pixels of 50 m make a 250 m block


def load_stack(path):
    """A stack file as a plain dict (format: docs/DATA_CONTRACT.md section 1)."""
    z = np.load(path)
    return {"hh": z["hh"], "hv": z["hv"], "cov": z["cov"], "T": Affine(*z["T"]), "epsg": int(z["crs"]),
            "dates": [str(d) for d in z["dates"]]}


def to_date(yyyymmdd):
    return date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))


def lonlat(stack):
    """Longitude and latitude of every pixel centre."""
    rows, cols = stack["cov"].shape
    c, r = np.meshgrid(np.arange(cols) + 0.5, np.arange(rows) + 0.5)
    x, y = stack["T"] * (c, r)
    return Transformer.from_crs(stack["epsg"], 4326, always_xy=True).transform(x, y)


def block_mean(a, size=BLOCK):
    """Mean over a size by size window around each pixel, ignoring NaN. NaN where under half the window has data."""
    have = np.isfinite(a).astype("float32")
    total = uniform_filter(np.nan_to_num(a), size, mode="nearest")
    share = uniform_filter(have, size, mode="nearest")
    return np.where(share > 0.5, total / np.maximum(share, 1e-6), np.nan).astype("float32")


def write_layer(path, a, stack, **tags):
    """Write one float32 GeoTIFF on the stack's grid (format: docs/DATA_CONTRACT.md section 2)."""
    with rasterio.open(path, "w", driver="GTiff", dtype="float32", count=1, height=a.shape[0], width=a.shape[1],
                       crs=f"EPSG:{stack['epsg']}", transform=stack["T"], nodata=np.nan, compress="DEFLATE",
                       predictor=3, tiled=True) as dst:
        dst.write(a.astype("float32"), 1)
        dst.update_tags(**{k: str(v) for k, v in tags.items()})
