# Written with Super Intelligence (SI) assistance.
"""Release grids and non-overlapping 250 m samples for Track 5."""
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import rasterio


@dataclass(frozen=True)
class Grid:
    shape: tuple
    transform: object
    crs: object


def _read(path):
    with rasterio.open(path) as src:
        if src.count != 1 or src.crs is None or src.crs.to_epsg() != 32750:
            raise ValueError(f"Expected a single band in EPSG:32750 in {path}")
        t = src.transform
        if not np.allclose([t.a, t.b, t.d, t.e], [50, 0, 0, -50], rtol=0, atol=1e-7):
            raise ValueError(f"Expected a north-up 50 m grid in {path}")
        values = src.read(1, masked=True).astype("float64").filled(np.nan)
        return values, Grid(values.shape, t, src.crs), src.tags()


def read_grid(path):
    values, grid, _ = _read(path)
    return values, grid


def read_drydown(layers, site, track):
    """Reject a swapped orbit or incompatible acquisition window before ranking it."""
    path = layers / f"drydown_{site}_{track}.tif"
    values, grid, tags = _read(path)
    if (tags.get("layer"), tags.get("units"), tags.get("track")) != ("HH dry-down", "dB", track):
        raise ValueError(f"{path.name}: expected the HH dry-down in dB for track {track}")
    early = tags.get("first_passes", "").split(",")
    late = tags.get("late_passes", "").split(",")
    dates = early + late
    cutoff = tags.get("dry_until", "")
    if len(early) not in (1, 2) or len(late) != 2 or dates != sorted(set(dates)) or late[-1] > cutoff:
        raise ValueError(f"{path.name}: inconsistent first/late passes or cutoff")
    for day in [*dates, cutoff]:
        if len(day) != 8 or not day.isascii() or not day.isdigit():
            raise ValueError(f"{path.name}: invalid acquisition date {day!r}")
        datetime.strptime(day, "%Y%m%d")
    return values, grid, tags


def same_grid(*grids):
    if not grids or any(grid != grids[0] for grid in grids[1:]):
        raise ValueError("Inputs must have identical dimensions, CRS and pixel alignment")


def centres(a):
    rows, cols = a.shape
    return a[2:rows // 5 * 5:5, 2:cols // 5 * 5:5]
