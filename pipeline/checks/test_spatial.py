# Written with Super Intelligence (SI) assistance.
"""Tests of the spatial helpers of the checks: block centres and the spread inside the reference forest."""
import unittest

import numpy as np

from pipeline.checks.common import centres
from pipeline.checks.forest import forest_metrics
from pipeline.checks.two_orbit import agreement


class SpatialChecks(unittest.TestCase):
    def test_rank_agreement_and_common_coverage(self):
        a = np.arange(24, dtype=float)
        b = a.copy()
        a[0], b[1] = np.nan, np.nan
        out = agreement(a, b)
        self.assertEqual(out["orbit_blocks"][0], 22)
        for metric in ("orbit_pearson", "orbit_spearman", "orbit_driest_tenth_overlap"):
            self.assertAlmostEqual(out[metric][0], 1)
        self.assertEqual(agreement(a, -b)["orbit_driest_tenth_overlap"][0], 0)

    def test_tied_cutoff(self):
        a = np.ones(20)
        b = np.ones(20)
        a[[1, 4, 6]], b[[4, 6]] = 0, 0
        self.assertEqual(agreement(a, b)["orbit_driest_tenth_overlap"][0], .5)

    def test_forest_purity_and_partial_edges(self):
        mask = np.ones((7, 19))
        mask[0, 0] = 0
        mask[0, 5:7] = 0
        change = np.full(mask.shape, np.nan)
        change[2, [2, 7, 12, 17]] = [-2, 20, 2, 99]
        self.assertEqual(centres(change).shape, (1, 3))
        out = forest_metrics(change, mask)
        self.assertEqual(out["forest_blocks"][0], 2)
        self.assertAlmostEqual(out["forest_p05"][0], -1.8)
        self.assertEqual(out["forest_p50"][0], 0)

    def test_same_orbit_renamed_or_other_season_cannot_confirm_agreement(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        import rasterio
        from rasterio.transform import from_origin
        from pipeline.checks.two_orbit import calculate
        with TemporaryDirectory() as td:
            layers = Path(td)
            for track in ("125", "061"):
                path = layers / f"drydown_west_{track}.tif"
                with rasterio.open(path, "w", driver="GTiff", width=50, height=50, count=1,
                                   dtype="float32", crs="EPSG:32750", transform=from_origin(500000, 9700000, 50, 50)) as ds:
                    ds.write(np.arange(2500, dtype="float32").reshape(50, 50), 1)
                    ds.update_tags(layer="HH dry-down", units="dB", track="125", dry_until="20261025",
                                   first_passes="20260622,20260704", late_passes="20261008,20261020")
            with self.assertRaisesRegex(ValueError, "track 061"):
                calculate(layers, "west")
            with rasterio.open(path, "r+") as ds:
                ds.update_tags(track="061", dry_until="20261110")
            with self.assertRaisesRegex(ValueError, "different seasonal cutoffs"):
                calculate(layers, "west")
