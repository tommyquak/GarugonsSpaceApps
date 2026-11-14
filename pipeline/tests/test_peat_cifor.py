# Written with Super Intelligence (SI) assistance.
"""Tests for the CIFOR peat cross-check on small synthetic maps where the right answer is known."""
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "context"))
import peat_cifor  # noqa: E402

EDGE_LON, GAP_LON = 114.0, 114.03   # peat west of EDGE_LON; CIFOR has no data east of GAP_LON
BBOX = (113.6, -3.2, 114.3, -2.4)


def cifor_source():
    """A lon/lat map like CIFOR's, 0.001 degree cells: peat (1) west of 114.0 E, not peat (0) east of it, no data (16) east of 114.03 E."""
    T = from_origin(113.0, -2.0, 0.001, 0.001)
    rows, cols = 2000, 2000
    lon = 113.0 + (np.arange(cols) + 0.5) * 0.001
    a = np.where(lon < EDGE_LON, 1, 0).astype("uint8")[None, :].repeat(rows, 0)
    a[:, lon >= GAP_LON] = 16
    mem = MemoryFile()
    with mem.open(driver="GTiff", width=cols, height=rows, count=1, dtype="uint8", crs="EPSG:4326", transform=T, nodata=16) as dst:
        dst.write(a, 1)
    return mem


def utm_profile():
    """A 50 m UTM 50S grid, 10 km square, that straddles 114.0 E near 2.6 S."""
    x0, y0 = Transformer.from_crs(4326, 32750, always_xy=True).transform(113.97, -2.6)
    return {"driver": "GTiff", "dtype": "float32", "count": 1, "width": 200, "height": 200, "crs": rasterio.CRS.from_epsg(32750),
            "transform": rasterio.Affine(50, 0, x0, 0, -50, y0), "nodata": np.nan}


def test_on_grid_puts_the_boundary_in_place_and_keeps_no_data():
    profile = utm_profile()
    with cifor_source() as mem, mem.open() as src:
        peat = peat_cifor.on_grid(src, BBOX, profile)
    T = profile["transform"]
    rows, cols = np.mgrid[0:200, 0:200]
    xs, ys = T * (cols + 0.5, rows + 0.5)
    lon, _ = Transformer.from_crs(32750, 4326, always_xy=True).transform(xs, ys)
    clear = 0.002    # two source cells either side of an edge can go either way
    assert np.all(peat[lon < EDGE_LON - clear] == 1)
    assert np.all(peat[(lon > EDGE_LON + clear) & (lon < GAP_LON - clear)] == 0)
    assert np.all(np.isnan(peat[lon > GAP_LON + clear]))


def test_compare_counts_what_each_map_calls_peat():
    # 10 cells: CIFOR has no data on the last two; PEATMAP calls cells 0-4 peat, CIFOR cells 2-6.
    cifor = np.array([0, 0, 1, 1, 1, 1, 1, 0, np.nan, np.nan], "float32")
    peatmap = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0, 1], "float32")
    m = peat_cifor.compare(cifor, peatmap)
    assert m["agreement"] == pytest.approx(4 / 8)            # cells 2, 3, 4 and 7 agree, of the 8 CIFOR covers
    assert m["chance"] == pytest.approx(5 / 8 * 5 / 8 + 3 / 8 * 3 / 8)   # both maps call 5 of those 8 cells peat
    assert m["cifor_in_peatmap"] == pytest.approx(3 / 5)     # of CIFOR's 5 peat cells, 3 are PEATMAP peat
    assert m["peatmap_in_cifor"] == pytest.approx(3 / 5)     # of PEATMAP's 5 covered peat cells, 3 are CIFOR peat
    assert "km2" not in m and "fire_share" not in m


def test_compare_redoes_the_headline_numbers_on_cifor_peat():
    cifor = np.array([1, 1, 1, 1, 0, 0], "float32")
    peatmap = np.array([1, 1, 0, 0, 1, 1], "float32")
    valid = np.array([1, 1, 1, 1, 1, 0], bool)
    strong = np.array([1, 0, 1, 0, 1, 0], bool)
    fire = np.array([1, 1, 0, 0, 0, 0], bool)
    m = peat_cifor.compare(cifor, peatmap, valid, strong, fire)
    assert m["km2"] == pytest.approx(4 * peat_cifor.KM2)
    assert m["fell_1db_km2"] == pytest.approx(2 * peat_cifor.KM2)            # cells 0 and 2
    assert m["fell_1db_km2_peatmap"] == pytest.approx(2 * peat_cifor.KM2)    # cells 0 and 4
    assert m["fire_share"] == pytest.approx(2 / 4)
