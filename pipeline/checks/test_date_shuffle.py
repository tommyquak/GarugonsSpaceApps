# Written with Super Intelligence (SI) assistance.
"""Focused tests for the exact paired date-shuffle check."""

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from pipeline.checks.date_shuffle import _enumerate_pairings, _fixed_block_means, calculate
from pipeline.checks.date_shuffle import _block_mean


class ExactShuffleTest(unittest.TestCase):
    def test_discards_incomplete_edge_blocks(self):
        values = np.arange(2 * 12 * 13, dtype="float32").reshape(2, 12, 13)

        means = _fixed_block_means(values)

        self.assertEqual(means.shape, (2, 2, 2))
        reference = np.stack([_block_mean(layer)[2:10:5, 2:10:5] for layer in values])
        np.testing.assert_allclose(means, reference, atol=2e-6)

    def test_enumerates_disjoint_unordered_pairs_and_includes_ties(self):
        series = np.arange(6, dtype="float32")[:, None, None]
        valid = np.ones((1, 1), dtype=bool)

        values, pairings = _enumerate_pairings(series, valid)

        self.assertEqual(len(pairings), math.comb(6, 2) * math.comb(4, 2))
        self.assertEqual(len(set(pairings)), len(pairings))
        self.assertTrue(all(not (set(early) & set(late)) for early, late in pairings))
        first = pairings.index(((0, 1), (4, 5)))
        self.assertEqual(values[first], 4.0)

        tied_series = np.ones((6, 1, 1), dtype="float32")
        tied_values, _ = _enumerate_pairings(tied_series, valid)
        self.assertEqual(np.count_nonzero(tied_values <= tied_values[0]), len(tied_values))

        one_early, one_pairings = _enumerate_pairings(series, valid, early_size=1, late_size=2)
        self.assertEqual(len(one_pairings), math.comb(6, 1) * math.comb(5, 2))
        self.assertTrue(all(len(early) == 1 and len(late) == 2 for early, late in one_pairings))
        self.assertTrue(all(not (set(early) & set(late)) for early, late in one_pairings))


class CalculateTest(unittest.TestCase):
    def _write_fixture(self, root: Path, mismatch: bool = False, invalid_centres: bool = False,
                       dates=None, early_count: int = 2, empty: bool = False):
        stacks = root / "stacks"
        layers = root / "layers"
        stacks.mkdir()
        layers.mkdir()
        dates = dates or ["20260622", "20260704", "20260716", "20260821", "20260902", "20260914"]
        # Each date image and its zero baseline offset stay paired. Values
        # darken monotonically so the tagged first/last pairing is strongest.
        if invalid_centres:
            hh = np.full((6, 25, 25), -10.0, dtype="float32")
            for block in range(13):
                row, col = divmod(block, 5)
                hh[:, row * 5:(row + 1) * 5, col * 5:(col + 1) * 5] -= np.arange(6, dtype="float32")[:, None, None]
        else:
            hh = np.stack([np.full((25, 25), -10.0 - i, dtype="float32") for i in range(6)])
        cov = np.ones((25, 25), dtype=bool)
        if empty:
            cov[:] = False
        hv = hh.copy()
        if invalid_centres:
            for block in range(13):
                row, col = divmod(block, 5)
                cov[row * 5 + 2, col * 5 + 2] = False
                hv[:, row * 5 + 2, col * 5 + 2] = np.nan
        transform = from_origin(500000, 9660000, 50, 50)
        np.savez(stacks / "west_125.npz", hh=hh, hv=hv, cov=cov,
                 T=np.asarray(tuple(transform)[:6]), crs=32750, dates=np.asarray(dates))
        (layers / "baseline_125.json").write_text(json.dumps({
            "dates": dates,
            "hh": {"offset_db": [0.0] * len(dates)},
        }))
        filtered = [_block_mean(layer) for layer in hh]
        early_indices = tuple(range(early_count))
        released = (filtered[-1] + filtered[-2]) * 0.5 - np.mean(
            np.stack([filtered[i] for i in early_indices]), axis=0)
        released[~cov] = np.nan
        if mismatch:
            released = np.zeros_like(released)
        with rasterio.open(layers / "drydown_west_125.tif", "w", driver="GTiff", dtype="float32",
                           count=1, width=25, height=25, crs="EPSG:32750", transform=transform,
                           nodata=np.nan) as dst:
            dst.write(released.astype("float32"), 1)
            dst.update_tags(layer="HH dry-down", units="dB", track="125", dry_until="20260914",
                            first_passes=",".join(dates[:early_count]),
                            late_passes=",".join(dates[-2:]))
        return stacks, layers, dates

    def test_calculates_exact_pair_fraction_against_release(self):
        with tempfile.TemporaryDirectory() as temp:
            stacks, layers, dates = self._write_fixture(Path(temp))

            metrics = calculate(stacks, layers, "west", "125")

            self.assertEqual(metrics["date_shuffle_pairing_count"][0], math.comb(len(dates), 2) * math.comb(len(dates) - 2, 2))
            self.assertAlmostEqual(metrics["date_shuffle_observed_median_change"][0], -4.0)
            self.assertEqual(metrics["date_shuffle_tail_count"][0], 1)
            self.assertEqual(metrics["date_shuffle_exact_p_one_sided"][0] * metrics["date_shuffle_pairing_count"][0],
                             metrics["date_shuffle_tail_count"][0])
            self.assertLessEqual(metrics["date_shuffle_exact_p_one_sided"][0], 0.05)
            self.assertEqual(metrics["date_shuffle_reconstruction_max_error"][0], 0.0)

    def test_calculates_single_dry_start_against_release(self):
        with tempfile.TemporaryDirectory() as temp:
            stacks, layers, dates = self._write_fixture(Path(temp), early_count=1)

            metrics = calculate(stacks, layers, "west", "125")

            self.assertEqual(metrics["date_shuffle_pairing_count"][0], math.comb(len(dates), 1) * math.comb(len(dates) - 1, 2))
            self.assertAlmostEqual(metrics["date_shuffle_observed_median_change"][0], -4.5)
            self.assertEqual(metrics["date_shuffle_tail_count"][0], 1)
            self.assertEqual(metrics["date_shuffle_reconstruction_max_error"][0], 0.0)

    def test_rejects_mismatch_with_released_drydown(self):
        with tempfile.TemporaryDirectory() as temp:
            stacks, layers, _ = self._write_fixture(Path(temp), mismatch=True)

            with self.assertRaisesRegex(ValueError, "reconstruction differs"):
                calculate(stacks, layers, "west", "125")

    def test_rejects_empty_released_drydown_without_numeric_result(self):
        with tempfile.TemporaryDirectory() as temp:
            stacks, layers, _ = self._write_fixture(Path(temp), empty=True)

            with self.assertRaisesRegex(ValueError, "no finite pixels"):
                calculate(stacks, layers, "west", "125")

    def test_excludes_blocks_whose_released_center_is_nodata(self):
        with tempfile.TemporaryDirectory() as temp:
            stacks, layers, _ = self._write_fixture(Path(temp), invalid_centres=True)

            metrics = calculate(stacks, layers, "west", "125")

            self.assertEqual(metrics["date_shuffle_block_count"][0], 12)
            self.assertAlmostEqual(metrics["date_shuffle_observed_median_change"][0], 0.0)
            self.assertEqual(metrics["date_shuffle_exact_p_one_sided"][0], 1.0)

    def test_rejects_duplicate_or_out_of_order_stack_dates(self):
        malformed_dates = (
            ["20260622", "20260704", "20260716", "20260716", "20260902", "20260914"],
            ["20260622", "20260704", "20260821", "20260716", "20260902", "20260914"],
        )
        for dates in malformed_dates:
            with self.subTest(dates=dates), tempfile.TemporaryDirectory() as temp:
                stacks, layers, _ = self._write_fixture(Path(temp), dates=dates)
                with self.assertRaisesRegex(ValueError, "unique and strictly increasing"):
                    calculate(stacks, layers, "west", "125")


if __name__ == "__main__":
    unittest.main()
