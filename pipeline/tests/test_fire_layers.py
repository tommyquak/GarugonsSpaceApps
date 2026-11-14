# Written with Super Intelligence (SI) assistance.
"""Tests for the fire layers on a small synthetic grid where the right answer is known."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "context"))
import fire_layers  # noqa: E402

ROWS = COLS = 100
T = rasterio.Affine(50, 0, 500000, 0, -50, 9700000)
EPSG = 32750
DRY_UNTIL = "20261025"
# (row, col, day, confidence, pixel size in km). Peat is the left half of the grid.
DETECTIONS = [
    (20, 20, "2026-08-01", "n", 0.4),   # on peat, in the dry season
    (40, 80, "2026-10-25", "n", 0.4),   # off peat, on the last dry day itself: kept
    (60, 70, "2026-10-30", "h", 0.4),   # off peat, after the rain returned: left out of fire_before_rain
    (80, 30, "2026-09-01", "l", 0.4),   # low confidence: dropped everywhere
]


def lonlat(row, col):
    x, y = T * (col + 0.5, row + 0.5)
    return Transformer.from_crs(EPSG, 4326, always_xy=True).transform(x, y)


def make_inputs(tmp_path):
    layers, firms = tmp_path / "layers", tmp_path / "firms"
    layers.mkdir()
    firms.mkdir()
    profile = dict(driver="GTiff", dtype="float32", count=1, width=COLS, height=ROWS, crs=f"EPSG:{EPSG}", transform=T, nodata=np.nan)
    with rasterio.open(layers / "drydown_west_125.tif", "w", **profile) as dst:
        dst.write(np.zeros((ROWS, COLS), "float32"), 1)
    peat = np.zeros((ROWS, COLS), "float32")
    peat[:, :COLS // 2] = 1
    with rasterio.open(layers / "peat_peatmap_west.tif", "w", **profile) as dst:
        dst.write(peat, 1)
    with open(firms / "firms_viirs.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["latitude", "longitude", "acq_date", "confidence", "scan", "track"])
        for row, col, day, conf, size in DETECTIONS:
            lon, lat = lonlat(row, col)
            w.writerow([lat, lon, day, conf, size, size])
    return layers, firms


def run(tmp_path, monkeypatch, *extra):
    layers, firms = make_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)     # validation.json is written under the working directory
    fire_layers.main(["--site", "west", "--firms", str(firms), "--layers", str(layers), *extra])
    return layers, json.loads((tmp_path / "pipeline/out/validation.json").read_text())


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def test_without_dry_until_nothing_new_is_written(tmp_path, monkeypatch):
    layers, v = run(tmp_path, monkeypatch)
    assert (layers / "fire_days_west.tif").exists()
    assert not (layers / "fire_before_rain_west.tif").exists()
    assert "fire_before_rain_km2_west" not in v


def test_fire_days_is_unchanged_by_the_window(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    plain, _ = run(tmp_path / "a", monkeypatch)
    windowed, _ = run(tmp_path / "b", monkeypatch, "--dry-until", DRY_UNTIL)
    for name in ("fire_days_west.tif", "fire_days_1km_west.tif"):
        assert np.array_equal(read(plain / name), read(windowed / name))


def test_window_keeps_fire_up_to_the_last_dry_day_only(tmp_path, monkeypatch):
    layers, v = run(tmp_path, monkeypatch, "--dry-until", DRY_UNTIL)
    every, before = read(layers / "fire_days_west.tif"), read(layers / "fire_before_rain_west.tif")
    assert every[20, 20] == before[20, 20] == 1      # dry-season fire: in both
    assert every[40, 80] == before[40, 80] == 1      # on the last dry day: in both
    assert every[60, 70] == 1 and before[60, 70] == 0  # after the rain: only in fire_days
    assert every[80, 30] == before[80, 30] == 0      # low confidence: in neither
    wide = read(layers / "fire_before_rain_1km_west.tif")
    assert wide[20, 35] == 1 and before[20, 35] == 0   # 750 m away: inside 1 km, outside the 200 m footprint
    assert wide[60, 70] == 0
    assert v["fire_detections_after_dry_west"]["value"] == 1
    assert v["fire_detections_west"]["value"] == 3


def test_window_areas_on_and_off_peat(tmp_path, monkeypatch):
    _, v = run(tmp_path, monkeypatch, "--dry-until", DRY_UNTIL)
    one_footprint = float(fire_layers.disk(4).sum() * fire_layers.KM2)   # 200 m reach on a 50 m grid
    half = ROWS * COLS // 2
    assert v["fire_before_rain_km2_on_peat_west"]["value"] == pytest.approx(one_footprint, abs=1e-4)
    assert v["fire_before_rain_km2_off_peat_west"]["value"] == pytest.approx(one_footprint, abs=1e-4)
    assert v["fire_before_rain_km2_west"]["value"] == pytest.approx(2 * one_footprint, abs=1e-4)
    assert v["fire_before_rain_share_on_peat_west"]["value"] == pytest.approx(fire_layers.disk(4).sum() / half, abs=1e-4)


def test_bad_date_is_refused(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        run(tmp_path, monkeypatch, "--dry-until", "2026-10-25")


def test_first_day_marks_the_same_cells_as_fire_days_and_keeps_the_earliest(tmp_path, monkeypatch):
    layers, _ = run(tmp_path, monkeypatch)
    first, days = read(layers / "fire_first_day_west.tif"), read(layers / "fire_days_west.tif")
    assert np.array_equal(np.isfinite(first), days > 0)
    assert first[20, 20] == 213     # 1 August 2026
    assert first[40, 80] == 298     # 25 October 2026
    assert first[60, 70] == 303     # 30 October 2026
    assert np.isnan(first[80, 30])  # a low-confidence detection leaves no mark


def test_first_day_is_the_earliest_where_two_days_overlap():
    by_day = {"2026-09-02": [((5, 5), 2)], "2026-08-20": [((5, 6), 2)]}
    first = fire_layers.first_day(by_day, (12, 12))
    assert first[5, 5] == first[5, 6] == 232   # 20 August reaches both cells
    assert first[5, 3] == 245                  # only 2 September reaches this one
    assert np.isnan(first[0, 0])
