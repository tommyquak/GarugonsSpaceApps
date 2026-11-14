# Written with Super Intelligence (SI) assistance.
"""Tests for the coherence burn flag on a small synthetic season where the right answer is known."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "context"))
import burn_flag  # noqa: E402
import fire_layers  # noqa: E402

N = 60
T = rasterio.Affine(50, 0, 500000, 0, -50, 9700000)
EPSG = 32750
PAIRS = [("20260704", "20260716"), ("20260716", "20260728"), ("20260728", "20260809"),
         ("20260809", "20260821"), ("20260821", "20260902"), ("20260902", "20260914")]
FIRE_CELL, FIRE_DAY, FIRE_PAIR = (15, 15), "2026-08-01", 2      # inside the third pair
BURN = (slice(10, 21), slice(10, 21))                          # on peat (left half): coherence collapses in the fire pair
CLEARING, CLEARING_PAIR = (slice(40, 51), slice(40, 51)), 4    # off peat, far from fire: collapses too, with no fire


def profile():
    return dict(driver="GTiff", dtype="float32", count=1, width=N, height=N, crs=f"EPSG:{EPSG}", transform=T, nodata=np.nan)


def write_tif(path, a, **tags):
    with rasterio.open(path, "w", **profile()) as dst:
        dst.write(a.astype("float32"), 1)
        if tags:
            dst.update_tags(**tags)


def make_inputs(tmp_path):
    rng = np.random.default_rng(1)
    layers, gunw, firms = tmp_path / "layers", tmp_path / "gunw", tmp_path / "firms"
    for d in (layers, gunw, firms):
        d.mkdir()
    write_tif(layers / "drydown_west_125.tif", np.zeros((N, N)))
    peat = np.zeros((N, N))
    peat[:, : N // 2] = 1
    write_tif(layers / "peat_peatmap_west.tif", peat)
    for i, (ref, sec) in enumerate(PAIRS):
        coh = 0.5 + 0.05 * i + rng.normal(0, 0.03, (N, N))     # each pair has its own scene-wide level
        if i == FIRE_PAIR:
            coh[BURN] = 0.05
        if i == CLEARING_PAIR:
            coh[CLEARING] = 0.05
        write_tif(gunw / f"g{i}_coh.tif", np.clip(coh, 0, 1), track_number="125", reference_date=ref, secondary_date=sec)
    write_tif(gunw / "long_coh.tif", np.full((N, N), 0.1), track_number="125", reference_date="20260716", secondary_date="20260821")
    write_tif(gunw / "other_coh.tif", np.full((N, N), 0.1), track_number="61", reference_date="20260712", secondary_date="20260724")
    lon, lat = Transformer.from_crs(EPSG, 4326, always_xy=True).transform(*(T * (FIRE_CELL[1] + 0.5, FIRE_CELL[0] + 0.5)))
    with open(firms / "firms_VIIRS_SNPP.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["latitude", "longitude", "acq_date", "confidence", "scan", "track"], [lat, lon, FIRE_DAY, "n", 0.4, 0.4]])
    return layers, gunw, firms


def run(tmp_path, monkeypatch):
    layers, gunw, firms = make_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)
    burn_flag.main(["--site", "west", "--track", "125", "--gunw", str(gunw), "--firms", str(firms), "--layers", str(layers)])
    with rasterio.open(layers / "burn_flag_west_125.tif") as src:
        flag = src.read(1)
    return flag, json.loads((tmp_path / "pipeline/out/validation.json").read_text())


def test_only_12_day_pairs_of_the_track_are_used(tmp_path):
    _, gunw, _ = make_inputs(tmp_path)
    with rasterio.open(tmp_path / "layers" / "drydown_west_125.tif") as src:
        pairs, coh = burn_flag.load_pairs(gunw, "125", src.profile)
    assert pairs == PAIRS and coh.shape == (len(PAIRS), N, N)


def test_drops_remove_the_scene_level_and_the_cells_own_level():
    coh = np.array([[[0.5, 0.3]], [[0.6, 0.4]], [[0.7, 0.5]], [[0.8, 0.1]]], "float32")   # 4 pairs, 1 x 2 cells
    fire = np.zeros(coh.shape, bool)
    fire[3, 0, 1] = True                    # the second cell burned in the last pair
    never = np.array([[True, False]])
    d = burn_flag.drops(coh, fire, never)
    assert np.allclose(d[:, 0, 0], 0)       # the never-fire cell only follows the scene: no drop
    assert d[3, 0, 1] == pytest.approx((0.1 - 0.8) - (-0.2))   # its fire pair against its usual 0.2 below the scene


def test_flag_finds_the_burn_and_the_clearing(tmp_path, monkeypatch):
    flag, v = run(tmp_path, monkeypatch)
    assert flag[BURN].all() and flag[CLEARING].all()
    assert v["coh_pairs_west_125"]["value"] == len(PAIRS)
    assert v["coh_flag_hit_rate_on_peat_west_125"]["value"] == 1
    assert v["coh_flag_timing_on_peat_west_125"]["value"] == 1
    assert v["coh_flag_timing_chance_on_peat_west_125"]["value"] == pytest.approx(1 / len(PAIRS), abs=1e-3)   # one fire pair of six
    assert v["coh_drop_median_fire_pairs_west_125"]["value"] < -0.3
    assert abs(v["coh_drop_median_clear_pairs_west_125"]["value"]) < 0.02
    assert v["coh_flag_no_fire_km2_off_peat_west_125"]["value"] >= 11 * 11 * fire_layers.KM2   # the clearing


def test_two_orbits_that_see_the_same_ground_agree(tmp_path, monkeypatch):
    layers, gunw, firms = make_inputs(tmp_path)
    write_tif(layers / "drydown_west_061.tif", np.zeros((N, N)))
    for f in sorted(gunw.glob("g*_coh.tif")):          # the other orbit sees the same changes, with its own noise
        with rasterio.open(f) as src:
            a, tags = src.read(1), src.tags()
        noise = np.random.default_rng(int(f.stem[1])).normal(0, 0.03, a.shape)
        write_tif(gunw / f"o{f.stem}.tif", np.clip(a + noise, 0, 1), track_number="61",
                  reference_date=tags["reference_date"], secondary_date=tags["secondary_date"])
    monkeypatch.chdir(tmp_path)
    common = ["--site", "west", "--gunw", str(gunw), "--firms", str(firms), "--layers", str(layers)]
    burn_flag.main(["--track", "125", *common])
    burn_flag.main(["--track", "061", "--other-track", "125", *common])
    v = json.loads((tmp_path / "pipeline/out/validation.json").read_text())
    assert v["coh_flag_two_orbit_overlap_on_peat_west_061_125"]["value"] > 0.5
    assert v["coh_drop_two_orbit_spearman_on_peat_west_061_125"]["value"] > 0.3


def test_too_few_pairs_is_refused(tmp_path, monkeypatch):
    layers, gunw, firms = make_inputs(tmp_path)
    for f in sorted(gunw.glob("g*_coh.tif"))[3:]:
        f.unlink()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        burn_flag.main(["--site", "west", "--track", "125", "--gunw", str(gunw), "--firms", str(firms), "--layers", str(layers)])
