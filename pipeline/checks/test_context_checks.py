# Written with Super Intelligence (SI) assistance.
"""Focused tests for rain recovery and peat-split checks."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter
from rasterio.transform import from_origin

from pipeline.checks.peat_split import calculate as calculate_peat_split
from pipeline.checks.recovery import audit_hv_absolute, calculate as calculate_recovery


def _write(path: Path, values: np.ndarray, *, transform=None, tags=None, nodata=np.nan) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1],
                       count=1, dtype="float32", crs="EPSG:32750",
                       transform=transform or from_origin(100_000, 9_700_000, 50, 50),
                       nodata=nodata) as dst:
        dst.write(values.astype("float32"), 1)
        if tags:
            dst.update_tags(**tags)


def _block_grid(values: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(values.astype("float32"), 5, axis=0), 5, axis=1)


class RecoveryCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.layers = Path(self.tmp.name)
        self.rain_date = "2026-10-25"
        (self.layers / "rain_daily_west.json").write_text(json.dumps({self.rain_date: 18.5}))
        grid = np.arange(100, dtype="float32").reshape(10, 10) / 10
        for track, first, late in (("061", "20260618,20260630", "20261004,20261016"),
                                   ("125", "20260622,20260704", "20261008,20261020")):
            _write(self.layers / f"drydown_west_{track}.tif", _block_grid(-grid), tags={
                "layer": "HH dry-down", "units": "dB", "track": track, "dry_until": "20261025",
                "first_passes": first, "late_passes": late,
            })
        for orbit in ("061", "125"):
            for pol in ("hh", "hv"):
                _write(self.layers / f"recovery_{pol}_west_{orbit}.tif", _block_grid(grid / 5), tags={
                    "track": orbit, "polarization": pol.upper(),
                    "late_passes": "20261004,20261016" if orbit == "061" else "20261008,20261020",
                    "after_pass": "20261028" if orbit == "061" else "20261101",
                    "units": "dB", "layer": f"{pol.upper()} rebound after the rain",
                })

    def tearDown(self):
        self.tmp.cleanup()

    def test_both_orbits_pair_recovery_with_other_orbit_drydown(self):
        result = calculate_recovery(self.layers, "west", "061", self.rain_date)
        self.assertEqual(result["recovery_061_hh_paired_n"][0], 100)
        self.assertGreater(result["recovery_061_hh_drydown_spearman_r"][0], 0.99)
        self.assertAlmostEqual(result["recovery_061_hh_median_db"][0], 0.99)
        self.assertIn("positive daily total 18.5 mm on supplied date", result["recovery_061_hv_median_db"][2])
        self.assertIn("does not by itself establish the onset", result["recovery_061_hv_median_db"][2])
        other = calculate_recovery(self.layers, "west", "125", self.rain_date)
        self.assertEqual(other["recovery_125_hh_paired_n"][0], 100)
        self.assertIn("positive daily total 18.5 mm on supplied date", other["recovery_125_hh_median_db"][2])
        (self.layers / "rain_daily_west.json").unlink()
        exploratory = calculate_recovery(self.layers, "west", "125", self.rain_date)
        self.assertIn("exploratory", exploratory["recovery_125_hh_median_db"][2])

    def test_rejects_bad_rain_record_when_supplied(self):
        (self.layers / "rain_daily_west.json").write_text(json.dumps({self.rain_date: 0}))
        with self.assertRaisesRegex(ValueError, "not positive"):
            calculate_recovery(self.layers, "west", "061", self.rain_date)

    def test_rejects_missing_provenance_and_bad_date_pair(self):
        path = self.layers / "recovery_hh_west_061.tif"
        _write(path, _block_grid(np.ones((10, 10))), tags={"track": "125"})
        with self.assertRaisesRegex(ValueError, "provenance"):
            calculate_recovery(self.layers, "west", "061")

    def test_rain_must_be_strictly_between_both_late_passes_and_after_pass(self):
        (self.layers / "rain_daily_west.json").write_text(json.dumps({"2026-10-16": 18.5, "2026-10-28": 12.0}))
        with self.assertRaisesRegex(ValueError, "not bracketed"):
            calculate_recovery(self.layers, "west", "061", "2026-10-16")
        with self.assertRaisesRegex(ValueError, "not bracketed"):
            calculate_recovery(self.layers, "west", "061", "2026-10-28")

    def test_hh_hv_must_match_dates_and_share_the_same_three_layer_cohort(self):
        hv = self.layers / "recovery_hv_west_061.tif"
        _write(hv, _block_grid(np.arange(100).reshape(10, 10) / 50), tags={
            "track": "061", "polarization": "HV", "late_passes": "20261005,20261016",
            "after_pass": "20261028", "units": "dB", "layer": "HV rebound after rain",
        })
        with self.assertRaisesRegex(ValueError, "do not match"):
            calculate_recovery(self.layers, "west", "061")
        _write(hv, _block_grid(np.arange(100).reshape(10, 10) / 50), tags={
            "track": "061", "polarization": "HV", "late_passes": "20261004,20261016",
            "after_pass": "20261028", "units": "dB", "layer": "HV rebound after rain",
        })
        with rasterio.open(hv, "r+") as dst:
            data = dst.read(1)
            data[2, 7] = np.nan
            dst.write(data, 1)
        with rasterio.open(self.layers / "drydown_west_125.tif", "r+") as dst:
            data = dst.read(1)
            data[2, 2] = np.nan
            dst.write(data, 1)
        shared = calculate_recovery(self.layers, "west", "061")
        self.assertEqual(shared["recovery_061_hh_paired_n"][0], 98)
        self.assertEqual(shared["recovery_061_hv_paired_n"][0], 98)
        self.assertAlmostEqual(shared["recovery_061_hh_median_db"][0], 1.01)
        self.assertAlmostEqual(shared["recovery_061_hv_median_db"][0], 1.01)

    def test_recovery_must_match_its_drydown_window_and_opposite_cutoff(self):
        dry = self.layers / "drydown_west_061.tif"
        _write(dry, _block_grid(-np.ones((10, 10))), tags={
            "layer": "HH dry-down", "units": "dB", "track": "061", "dry_until": "20261024",
            "first_passes": "20260618,20260630", "late_passes": "20261004,20261016",
        })
        with self.assertRaisesRegex(ValueError, "different dry-until cutoffs"):
            calculate_recovery(self.layers, "west", "061")
        _write(dry, _block_grid(-np.ones((10, 10))), tags={
            "layer": "HH dry-down", "units": "dB", "track": "061", "dry_until": "20261025",
            "first_passes": "20260618,20260630", "late_passes": "20261004,20261016",
        })
        with rasterio.open(self.layers / "recovery_hh_west_061.tif", "r+") as dst:
            dst.update_tags(late_passes="20261005,20261016")
        with self.assertRaisesRegex(ValueError, "do not match"):
            calculate_recovery(self.layers, "west", "061")

    def test_driest_decile_has_fixed_size_when_values_tie(self):
        strength = np.linspace(0, 0.5, 100, dtype="float32")
        strength[:15] = 1
        _write(self.layers / "drydown_west_125.tif", _block_grid(-strength.reshape(10, 10)), tags={
            "layer": "HH dry-down", "units": "dB", "track": "125", "dry_until": "20261025",
            "first_passes": "20260622,20260704", "late_passes": "20261008,20261020",
        })
        result = calculate_recovery(self.layers, "west", "061")
        self.assertEqual(result["recovery_061_hh_driest_decile_n"][0], 10)
        self.assertAlmostEqual(result["recovery_061_hh_driest_decile_median_db"][0], 0.09)

    def test_sidecar_cannot_override_tiff_provenance(self):
        path = self.layers / "recovery_hh_west_061.tif"
        sidecar = path.with_suffix(path.suffix + ".json")
        sidecar.write_text(json.dumps({"track": "125"}))
        with self.assertRaisesRegex(ValueError, "sidecar conflicts"):
            calculate_recovery(self.layers, "west", "061")

    def test_hv_absolute_audit_holds_only_absolute_values_for_uniform_offset(self):
        stack_dir = self.layers / "stacks"
        stack_dir.mkdir()
        rows, cols = 50, 50
        yy, xx = np.mgrid[:rows, :cols]
        base = (xx + yy).astype("float32") / 100
        dates = ["20261004", "20261016", "20261028"]
        hv_stack = np.stack([base, base + 0.1, base + 0.4])
        np.savez(stack_dir / "west_061.npz", hv=hv_stack,
                 cov=np.ones((rows, cols), dtype=bool),
                 T=np.array(tuple(from_origin(100_000, 9_700_000, 50, 50))[:6]),
                 crs=np.array(32750), dates=np.array(dates))
        tags = {"track": "061", "units": "dB", "late_passes": "20261004,20261016",
                "after_pass": "20261028"}
        smoothed = uniform_filter(hv_stack[2], size=5, mode="nearest") - (
            uniform_filter(hv_stack[0], size=5, mode="nearest") +
            uniform_filter(hv_stack[1], size=5, mode="nearest")) / 2
        released = smoothed[2::5, 2::5] + 0.1
        _write(self.layers / "recovery_hv_west_061.tif", _block_grid(released),
               tags={**tags, "layer": "HV rebound after rain", "polarization": "HV"})
        _write(self.layers / "recovery_hh_west_061.tif", _block_grid(np.ones((10, 10)) * 0.3),
               tags={**tags, "layer": "HH rebound after rain", "polarization": "HH"})
        audit = audit_hv_absolute(stack_dir, self.layers, "west", "061")
        self.assertTrue(audit["available"])
        self.assertTrue(audit["rank_preserved"])
        self.assertTrue(audit["uniform_shift"])
        self.assertEqual(audit["hold_suffixes"], [
            "recovery_061_hv_median_db", "recovery_061_hv_driest_decile_median_db",
        ])

    def test_hv_absolute_audit_skips_historical_stack_missing_tagged_date(self):
        stack_dir = self.layers / "stacks"
        stack_dir.mkdir()
        np.savez(stack_dir / "west_061.npz", hv=np.zeros((2, 50, 50), dtype="float32"),
                 cov=np.ones((50, 50), dtype=bool),
                 T=np.array(tuple(from_origin(100_000, 9_700_000, 50, 50))[:6]),
                 crs=np.array(32750), dates=np.array(["20261004", "20261016"]))
        result = audit_hv_absolute(stack_dir, self.layers, "west", "061")
        self.assertFalse(result["available"])
        self.assertEqual(result["hold_suffixes"], [])


class PeatSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.layers = Path(self.tmp.name)
        dry = np.array([[1, 1, 0, 0], [1, 0, 0, 1], [0, 1, 1, 0], [0, 0, 1, 1]], dtype="float32")
        peat_official = np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]], dtype="float32")
        peat_cifor = np.array([[1, 0, 0, 0], [1, 0, 0, 1], [0, 1, 1, 1], [0, 0, 1, 1]], dtype="float32")
        peatmap = np.array([[1, 1, 1, 1], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]], dtype="float32")
        _write(self.layers / "dried_west.tif", dry, tags={
            "layer": "dried on both orbits", "floor_061": "-0.33", "floor_125": "-0.29",
        })
        _write(self.layers / "peat_official_west.tif", peat_official)
        _write(self.layers / "peat_cifor_west.tif", peat_cifor)
        _write(self.layers / "peat_peatmap_west.tif", peatmap, tags={"source": "Xu et al. PEATMAP"})
        _write(self.layers / "fire_days_west.tif", np.array([[1, 0, 0, 0]] * 4, dtype="float32"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_areas_and_shares_are_split_for_both_peat_maps(self):
        result = calculate_peat_split(self.layers, "west")
        self.assertAlmostEqual(result["dried_peat_official_on_km2"][0], 0.015)
        self.assertAlmostEqual(result["dried_peat_official_on_share"][0], 0.75)
        self.assertAlmostEqual(result["dried_peat_official_off_km2"][0], 0.005)
        self.assertAlmostEqual(result["dried_peat_cifor_on_km2"][0], 0.0175)
        self.assertAlmostEqual(result["dried_peat_cifor_off_km2"][0], 0.0025)
        self.assertAlmostEqual(result["dried_peat_peatmap_on_km2"][0], 0.01)
        self.assertAlmostEqual(result["dried_peat_peatmap_off_km2"][0], 0.01)
        self.assertIn("Xu et al. PEATMAP", result["dried_peat_peatmap_on_km2"][2])
        self.assertIn("fire_peat_cifor_on_share", result)

    def test_missing_peat_is_explicit_no_data_and_does_not_block_dry_area(self):
        (self.layers / "peat_cifor_west.tif").unlink()
        result = calculate_peat_split(self.layers, "west")
        self.assertAlmostEqual(result["dried_peat_official_on_km2"][0], 0.015)
        self.assertIsNone(result["dried_peat_cifor_on_km2"][0])
        self.assertIn("Missing peat map", result["dried_peat_cifor_on_km2"][2])

    def test_fire_is_optional_and_nodata_is_not_off_peat(self):
        (self.layers / "fire_days_west.tif").unlink()
        with rasterio.open(self.layers / "peat_official_west.tif", "r+") as dst:
            data = dst.read(1)
            data[0, 0] = np.nan
            dst.write(data, 1)
        result = calculate_peat_split(self.layers, "west")
        self.assertAlmostEqual(result["dried_peat_official_on_km2"][0], 0.0125)
        self.assertAlmostEqual(result["dried_peat_official_unknown_valid_km2"][0], 0.0025)
        self.assertAlmostEqual(result["dried_peat_official_off_valid_km2"][0], 0.02)
        self.assertIsNone(result["fire_peat_official_on_km2"][0])
        self.assertIn("Fire layer missing", result["fire_peat_official_on_km2"][2])

    def test_zero_cannot_be_a_nodata_code_but_declared_255_is_masked(self):
        values = np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]], dtype="float32")
        _write(self.layers / "peat_official_west.tif", values, nodata=0)
        with self.assertRaisesRegex(ValueError, "nodata conflicts"):
            calculate_peat_split(self.layers, "west")
        _write(self.layers / "peat_official_west.tif", np.array([
            [255, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1],
        ], dtype="float32"), nodata=255)
        result = calculate_peat_split(self.layers, "west")
        self.assertAlmostEqual(result["dried_peat_official_unknown_valid_km2"][0], 0.0025)
        self.assertAlmostEqual(result["dried_peat_official_on_km2"][0], 0.0125)


if __name__ == "__main__":
    unittest.main()
