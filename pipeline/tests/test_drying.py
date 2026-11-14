# Written with Super Intelligence (SI) assistance.
"""Tests for the drying steps on a small synthetic stack where the right answer is known."""
import json

import numpy as np
import rasterio

import common
import drydown
import vjson


def make_stack(rows=60, cols=60, dates=("20260601", "20260613", "20260625", "20260707", "20260719", "20260731")):
    """Flat ground at -6 dB. The right half darkens by 2 dB over the season. Each date carries a scene-wide shift."""
    shift = np.array([0.3, -0.2, 0.1, -0.4, 0.2, 0.0], "float32")
    fall = np.linspace(0, -2, len(dates)).astype("float32")
    hh = np.full((len(dates), rows, cols), -6.0, "float32") + shift[:, None, None]
    hh[:, :, cols // 2:] += fall[:, None, None]
    stack = {"hh": hh, "hv": hh - 6, "cov": np.ones((rows, cols), bool), "T": rasterio.Affine(50, 0, 500000, 0, -50, 9700000),
             "epsg": 32750, "dates": list(dates)}
    baseline = {"dates": list(dates), "hh": {"offset_db": (shift - shift.mean()).tolist()}, "hv": {"offset_db": (shift - shift.mean()).tolist()}}
    return stack, baseline, fall


def test_block_mean_ignores_nan_and_needs_half_the_window():
    a = np.full((20, 20), 2.0, "float32")
    a[5, 5] = np.nan
    out = common.block_mean(a)
    assert np.isclose(out[5, 5], 2.0)            # one missing sample does not matter
    a[:10, :] = np.nan
    out = common.block_mean(a)
    assert np.isnan(out[2, 10]) and np.isclose(out[15, 10], 2.0)


def test_normalised_removes_the_scene_wide_shift():
    stack, baseline, _ = make_stack()
    flat = drydown.normalised(stack, baseline)[:, 10, 10]     # left half: no real change
    assert np.ptp(flat) < 1e-5


def test_normalised_refuses_a_baseline_from_other_dates():
    import pytest
    stack, baseline, _ = make_stack()
    baseline["dates"] = baseline["dates"][::-1]
    with pytest.raises(SystemExit):
        drydown.normalised(stack, baseline)


def test_drydown_recovers_a_known_fall():
    stack, baseline, fall = make_stack()
    change, first, late = drydown.drydown(stack, baseline, "20260731")
    expected = fall[-2:].mean() - fall[:2].mean()               # mean of last two minus mean of first two
    assert first == ["20260601", "20260613"] and late == ["20260719", "20260731"]
    assert abs(change[30, 10]) < 1e-4                            # stable half
    assert np.isclose(change[30, 50], expected, atol=1e-4)       # darkening half, away from the boundary


def test_drydown_ignores_passes_after_the_rain():
    stack, baseline, fall = make_stack()
    stack["hh"][-1] += 5.0                                       # a wet pass that must not count as "late"
    change, _, late = drydown.drydown(stack, baseline, "20260719")
    assert late == ["20260707", "20260719"]
    assert np.isclose(change[30, 50], fall[3:5].mean() - fall[:2].mean(), atol=1e-4)


def test_series_bytes_round_trip_within_one_step():
    import series
    db = np.array([-29.9, -12.34, -6.0, 0.4], "float32")
    byte = np.clip(np.round((db - series.OFFSET) / series.SCALE), 1, 255)
    back = byte * series.SCALE + series.OFFSET
    assert np.all(np.abs(back - db) <= series.SCALE / 2 + 1e-6)
    assert byte.min() >= 1                                       # 0 is kept for "no data"


def test_validation_writer_adds_and_replaces(tmp_path):
    path = tmp_path / "validation.json"
    vjson.put("b_key", 1.23456789, "dB", "west", "test", path=path)
    vjson.put("a_key", 7, "blocks", "west", "test", path=path)
    vjson.put("b_key", 2.0, "dB", "west", "test", status="final", path=path)
    data = json.loads(path.read_text())
    assert list(data) == ["a_key", "b_key"]                      # sorted
    assert data["b_key"]["value"] == 2.0 and data["b_key"]["status"] == "final"
    assert data["a_key"]["status"] == "exploratory"
