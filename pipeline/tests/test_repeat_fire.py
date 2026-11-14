# Written with Super Intelligence (SI) assistance.
"""Tests for repeat fire on a small synthetic grid where the right answer is known."""
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
import repeat_fire  # noqa: E402

ROWS = COLS = 100
T = rasterio.Affine(50, 0, 500000, 0, -50, 9700000)
EPSG = 32750
R = 4                      # a 0.4 km VIIRS pixel reaches 200 m, 4 cells on a 50 m grid
A, B, C = (20, 20), (20, 35), (70, 80)   # A and B on peat (left half), C off it


def write_csv(folder, cells, day, conf="n"):
    folder.mkdir(parents=True)
    tf = Transformer.from_crs(EPSG, 4326, always_xy=True)
    with open(folder / "firms_VIIRS_SNPP.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["latitude", "longitude", "acq_date", "confidence", "scan", "track"])
        for row, col in cells:
            lon, lat = tf.transform(*(T * (col + 0.5, row + 0.5)))
            w.writerow([lat, lon, day, conf, 0.4, 0.4])


def run(tmp_path, monkeypatch):
    """2026 fire at A and B. 2015 had fire at A and a low-confidence one at B; 2019 had fire at C."""
    layers, history = tmp_path / "layers", tmp_path / "history"
    layers.mkdir()
    profile = dict(driver="GTiff", dtype="float32", count=1, width=COLS, height=ROWS, crs=f"EPSG:{EPSG}", transform=T, nodata=np.nan)
    now = fire_layers.stamp((ROWS, COLS), [A, B], [R, R]).astype("float32")
    peat = np.zeros((ROWS, COLS), "float32")
    peat[:, :COLS // 2] = 1
    for name, a in (("fire_days_west.tif", now), ("peat_peatmap_west.tif", peat)):
        with rasterio.open(layers / name, "w", **profile) as dst:
            dst.write(a, 1)
    write_csv(history / "2015", [A], "2015-09-10")
    with open(history / "2015" / "firms_MODIS.csv", "w", newline="") as fh:   # low confidence: dropped
        csv.writer(fh).writerows([["latitude", "longitude", "acq_date", "confidence", "scan", "track"],
                                  [*reversed(Transformer.from_crs(EPSG, 4326, always_xy=True).transform(*(T * (B[1] + 0.5, B[0] + 0.5)))),
                                   "2015-09-11", "10", 1.0, 1.0]])
    write_csv(history / "2019", [C], "2019-09-01")
    (history / "notes").mkdir()       # not a year: ignored
    monkeypatch.chdir(tmp_path)
    repeat_fire.main(["--site", "west", "--history", str(history), "--layers", str(layers)])
    with rasterio.open(layers / "fire_years_west.tif") as src:
        years = src.read(1)
    return years, json.loads((tmp_path / "pipeline/out/validation.json").read_text())


def test_fire_years_counts_earlier_seasons(tmp_path, monkeypatch):
    years, _ = run(tmp_path, monkeypatch)
    assert years[A] == 1 and years[C] == 1
    assert years[B] == 0            # only a low-confidence detection there, in 2015
    assert years[50, 5] == 0


def test_repeat_share_against_earlier_share(tmp_path, monkeypatch):
    _, v = run(tmp_path, monkeypatch)
    footprint = int(fire_layers.disk(R).sum())
    half = ROWS * COLS // 2
    assert v["fire_repeat_share_on_peat_west"]["value"] == pytest.approx(0.5, abs=1e-4)          # A repeats, B is new
    assert v["fire_earlier_share_on_peat_west"]["value"] == pytest.approx(footprint / half, abs=1e-4)
    assert v["fire_new_km2_on_peat_west"]["value"] == pytest.approx(footprint * fire_layers.KM2, abs=1e-4)
    assert v["fire_new_km2_off_peat_west"]["value"] == 0
    assert v["fire_share_on_peat_2015_west"]["value"] == pytest.approx(footprint / half, abs=1e-4)
    assert v["fire_share_off_peat_2019_west"]["value"] == pytest.approx(footprint / half, abs=1e-4)
    assert v["fire_share_on_peat_2019_west"]["value"] == 0


def test_no_year_folders_is_refused(tmp_path, monkeypatch):
    (tmp_path / "history").mkdir()
    (tmp_path / "layers").mkdir()
    with pytest.raises(SystemExit):
        repeat_fire.main(["--site", "west", "--history", str(tmp_path / "history"), "--layers", str(tmp_path / "layers")])
