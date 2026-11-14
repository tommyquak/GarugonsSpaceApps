# Written with Super Intelligence (SI) assistance.
"""Tests for the stack builder and the window arithmetic of the pull, on small synthetic inputs."""
import numpy as np
import rasterio

import build_stack
import pull_gcov


def test_multilook_averages_power_not_decibels():
    # One 5 by 5 block holding 24 samples of 1.0 and one of 101.0: the mean power is 5.0.
    a = np.ones((5, 5), "float32")
    a[2, 2] = 101.0
    out = build_stack.multilook(a)
    assert out.shape == (1, 1)
    assert np.isclose(out[0, 0], 5.0)


def test_multilook_needs_more_than_half_the_samples():
    a = np.ones((5, 10), "float32")
    a[:, :5].flat[:13] = np.nan     # left block keeps 12 of 25 samples: not enough
    a[:, 5:].flat[:12] = np.nan     # right block keeps 13 of 25: enough
    out = build_stack.multilook(a)
    assert np.isnan(out[0, 0]) and np.isclose(out[0, 1], 1.0)


def test_multilook_drops_the_ragged_edge():
    assert build_stack.multilook(np.ones((12, 17), "float32")).shape == (2, 3)


def test_granule_fields():
    name = "NISAR_L2_PR_GCOV_023_125_A_176_4005_DHDH_A_20260622T220711_20260622T220745_P05023_N_F_J_001"
    assert build_stack.granule_fields(name) == (125, "20260622")


def test_regrid_onto_the_same_grid_changes_nothing():
    rng = np.random.default_rng(0)
    a = rng.random((40, 50)).astype("float32")
    T = rasterio.Affine(50, 0, 500000, 0, -50, 9700000)
    like = {"cov": np.ones(a.shape, bool), "T": np.array(tuple(T)[:6]), "crs": 32750}
    out = build_stack.regrid(a, T, 32750, like)
    assert np.allclose(out, a, atol=1e-5)


def test_regrid_between_utm_zones_keeps_a_feature_in_place():
    # A bright square placed by longitude and latitude must land on the same ground after a zone change.
    from pyproj import Transformer
    T49 = rasterio.Affine(50, 0, 820000, 0, -50, 9700000)        # UTM 49S, east of its central meridian
    a = np.full((200, 200), 1.0, "float32")
    a[90:110, 90:110] = 10.0
    cx, cy = T49 * (100, 100)
    lon, lat = Transformer.from_crs(32749, 4326, always_xy=True).transform(cx, cy)
    x50, y50 = Transformer.from_crs(4326, 32750, always_xy=True).transform(lon, lat)
    T50 = rasterio.Affine(50, 0, x50 - 100 * 50, 0, -50, y50 + 100 * 50)
    like = {"cov": np.ones((200, 200), bool), "T": np.array(tuple(T50)[:6]), "crs": 32750}
    out = build_stack.regrid(a, T49, 32749, like)
    rows, cols = np.where(out > 5)
    assert abs(rows.mean() - 99.5) < 1.5 and abs(cols.mean() - 99.5) < 1.5


def test_window_covers_the_box_and_nothing_far_outside():
    # A 10 m grid in UTM 50S around 114 E, 2.8 S; y runs north to south as in the products.
    from pyproj import Transformer
    x0, y0 = Transformer.from_crs(4326, 32750, always_xy=True).transform(114.0, -2.8)
    x = x0 - 5000 + 10 * np.arange(1000)
    y = y0 + 5000 - 10 * np.arange(1000)
    bbox = (113.99, -2.81, 114.01, -2.79)
    r0, r1, c0, c1 = pull_gcov.window(x, y, 32750, bbox)
    back = Transformer.from_crs(32750, 4326, always_xy=True)
    west, north = back.transform(x[c0], y[r0])
    east, south = back.transform(x[c1 - 1], y[r1 - 1])
    assert west <= bbox[0] + 1e-4 and east >= bbox[2] - 1e-4 and south <= bbox[1] + 1e-4 and north >= bbox[3] - 1e-4
    assert (r1 - r0) < 260 and (c1 - c0) < 260     # the box is about 2.2 km, so about 220 pixels


def test_window_rejects_a_box_outside_the_granule():
    import pytest
    x = 500000 + 10 * np.arange(100)
    y = 9700000 - 10 * np.arange(100)
    with pytest.raises(ValueError):
        pull_gcov.window(x, y, 32750, (100.0, 10.0, 100.1, 10.1))
