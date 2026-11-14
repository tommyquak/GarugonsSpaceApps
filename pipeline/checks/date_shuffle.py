# Written with Super Intelligence (SI) assistance.
"""Exact early-versus-late date shuffle check for seasonal HH change.

For each admissible assignment, the tagged dry-start group has one or two
dates and the late group has two other dates. The date-specific images and
their baseline offsets stay together. The statistic is the median across
complete 250 m block centres of mean(late group) minus mean(dry-start group).
Every disjoint unordered assignment with those group sizes is enumerated,
with ties included in the one-sided darkening tail. Candidate dates begin at
the first tagged dry-start pass and end at ``dry_until``; no earlier passes
enter the null. This assumes dates are exchangeable within that dry-season
window despite potentially changing weather and unequal temporal spacing.

Run from the repository root with:
    python -m pipeline.checks.date_shuffle --stacks pipeline/out/stacks \
        --layers pipeline/out/layers --site west --track 125
"""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

from pipeline.checks.common import read_drydown


def _load_stack(path: Path) -> dict:
    with np.load(path) as saved:
        return {
            "hh": saved["hh"],
            "cov": saved["cov"],
            "T": rasterio.Affine(*saved["T"]),
            "epsg": int(saved["crs"]),
            "dates": [str(day) for day in saved["dates"]],
        }


def _block_mean(values: np.ndarray, size: int = 5) -> np.ndarray:
    """Independently reproduce the pipeline's moving-window 250 m mean."""
    have_data = np.isfinite(values).astype("float32")
    totals = uniform_filter(np.nan_to_num(values), size=size, mode="nearest")
    coverage = uniform_filter(have_data, size=size, mode="nearest")
    return np.where(coverage > 0.5, totals / np.maximum(coverage, 1e-6), np.nan).astype("float32")


def _fixed_block_means(values: np.ndarray) -> np.ndarray:
    """Compute independent, non-overlapping block means."""
    rows, cols = values.shape[-2:]
    complete_rows = rows // 5 * 5
    complete_cols = cols // 5 * 5
    values = values[..., :complete_rows, :complete_cols].astype("float64")
    nrows, ncols = complete_rows // 5, complete_cols // 5
    blocks = values.reshape(*values.shape[:-2], nrows, 5, ncols, 5)
    finite = np.isfinite(blocks)
    counts = finite.sum(axis=(-3, -1))
    totals = np.where(finite, blocks, 0.0).sum(axis=(-3, -1), dtype="float64")
    means = np.divide(totals, counts, out=np.full_like(totals, np.nan), where=counts >= 13)
    return means


def _date_index(dates: list[str], tagged_dates: str, tag_name: str,
                sizes: tuple[int, ...]) -> tuple[int, ...]:
    values = [day for day in tagged_dates.split(",") if day]
    if len(values) not in sizes or len(set(values)) != len(values) or any(day not in dates for day in values):
        allowed = " or ".join(str(size) for size in sizes)
        raise ValueError(f"{tag_name} must list {allowed} distinct dates present in the stack")
    return tuple(dates.index(day) for day in values)


def _group_mean(series: np.ndarray, indices: tuple[int, ...]) -> np.ndarray:
    if len(indices) == 1:
        return series[indices[0]]
    # Keep the legacy two-date arithmetic exactly unchanged.
    if len(indices) == 2:
        return (series[indices[0]] + series[indices[1]]) * 0.5
    return np.mean(series[list(indices)], axis=0)


def _paired_median(series: np.ndarray, valid: np.ndarray, early: tuple[int, ...],
                   late: tuple[int, ...]) -> float:
    change = _group_mean(series, late) - _group_mean(series, early)
    return float(np.median(change[valid]))


def _enumerate_pairings(series: np.ndarray, valid: np.ndarray, early_size: int = 2,
                        late_size: int = 2) -> tuple[np.ndarray, list[tuple[tuple[int, ...], tuple[int, ...]]]]:
    """Enumerate disjoint unordered assignments while preserving group sizes."""
    n_dates = series.shape[0]
    indices = range(n_dates)
    pairings = []
    statistics = []
    for early in itertools.combinations(indices, early_size):
        remaining = [i for i in indices if i not in early]
        for late in itertools.combinations(remaining, late_size):
            pairings.append((early, late))
            statistics.append(_paired_median(series, valid, early, late))
    return np.asarray(statistics, dtype="float64"), pairings


def calculate(stacks: Path, layers: Path, site: str, track: str) -> dict[str, tuple[object, str, str]]:
    """Return Track 5 metric suffixes mapped to (value, unit, note)."""
    stack_path = stacks / f"{site}_{track}.npz"
    stack = _load_stack(stack_path)
    baseline_path = layers / f"baseline_{track}.json"
    baseline = json.loads(baseline_path.read_text())
    if baseline.get("dates") != stack["dates"]:
        raise ValueError(f"baseline dates do not match {stack_path.name}")
    try:
        parsed_dates = [datetime.strptime(day, "%Y%m%d") for day in stack["dates"]]
    except ValueError as error:
        raise ValueError(f"{stack_path.name} contains an invalid acquisition date") from error
    if parsed_dates != sorted(set(parsed_dates)):
        raise ValueError(f"{stack_path.name} acquisition dates must be unique and strictly increasing")

    released, grid, tags = read_drydown(layers, site, track)
    if released.shape != stack["cov"].shape or grid.transform != stack["T"]:
        raise ValueError(f"dry-down layer grid does not match {stack_path.name}")
    if grid.crs.to_epsg() != stack["epsg"]:
        raise ValueError(f"dry-down layer CRS does not match {stack_path.name}")

    dry_until = tags["dry_until"]
    dates = stack["dates"]
    first = _date_index(dates, tags.get("first_passes", ""), "first_passes", (1, 2))
    late = _date_index(dates, tags.get("late_passes", ""), "late_passes", (2,))
    dry_start = dates[first[0]]
    use = [i for i, day in enumerate(dates) if dry_start <= day <= dry_until]
    if len(use) < len(first) + len(late):
        raise ValueError("not enough candidate passes from tagged dry start through dry_until")
    if any(i not in use for i in first + late) or set(first) & set(late):
        raise ValueError("tagged early and late dates must be distinct passes on or before dry_until")
    if first != tuple(use[:len(first)]) or late != tuple(use[-len(late):]):
        raise ValueError("tagged dry-start and late dates do not match candidate-window endpoints")

    # Keep every pass image attached to its own baseline offset, then build
    # smoothed 250 m values using the same function as the published layer.
    if len(baseline.get("hh", {}).get("offset_db", [])) != len(dates):
        raise ValueError(f"baseline HH offsets do not match {stack_path.name}")
    offsets = np.asarray(baseline["hh"]["offset_db"], dtype="float32")
    hh = stack["hh"] - offsets[:, None, None]
    smoothed = np.stack([_block_mean(hh[i]) for i in use])
    position = {stack_index: i for i, stack_index in enumerate(use)}
    early_positions = tuple(position[i] for i in first)
    late_positions = tuple(position[i] for i in late)
    reconstructed = (_group_mean(smoothed, late_positions) - _group_mean(smoothed, early_positions))
    reconstructed[~stack["cov"]] = np.nan
    comparable = np.isfinite(released) & np.isfinite(reconstructed)
    if not np.array_equal(np.isfinite(released), np.isfinite(reconstructed)):
        raise ValueError("released dry-down finite-pixel mask differs from reconstruction")
    if not np.any(comparable):
        raise ValueError("no finite pixels available for released-layer comparison")
    max_abs_error = float(np.max(np.abs(released[comparable] - reconstructed[comparable])))
    if max_abs_error > 1e-4:
        raise ValueError(f"released dry-down reconstruction differs by {max_abs_error:.4f} dB")

    # Match centres of the released raster and require support on every date
    # used by the shuffle, so every pairing uses the same block set.
    series = _fixed_block_means(hh[use])
    rows, cols = series.shape[1:]
    center_coverage = stack["cov"][2:rows * 5:5, 2:cols * 5:5]
    valid = center_coverage & np.all(np.isfinite(series), axis=0)
    if not np.any(valid):
        raise ValueError("no complete 250 m block centres are available")
    observed = _paired_median(series, valid, early_positions, late_positions)
    null_statistics, pairings = _enumerate_pairings(series, valid, len(early_positions), len(late_positions))
    # Since the statistic is negative for darkening, include all ties in the
    # left tail. This is the exact finite assignment fraction, with no
    # Monte-Carlo correction.
    tail_count = int(np.count_nonzero(null_statistics <= observed))
    p_value = float(tail_count / len(pairings))
    note = (f"Exact enumeration of {len(pairings)} disjoint unordered assignments preserving "
            f"group sizes ({len(early_positions)} dry-start, {len(late_positions)} late); "
            f"{int(valid.sum())} complete 250 m block centres; dry-start {tags['first_passes']}, "
            f"late {tags['late_passes']}; candidate dates through {dry_until}; "
            f"drydown reconstruction max error {max_abs_error:.6f} dB. Pair shuffling assumes "
            "exchangeable acquisition conditions, which seasonal weather may violate.")
    return {
        "date_shuffle_observed_median_change": (observed, "dB", note),
        "date_shuffle_exact_p_one_sided": (p_value, "exact permutation fraction", note),
        "date_shuffle_pairing_count": (len(pairings), "disjoint dry-start/late assignments", note),
        "date_shuffle_tail_count": (tail_count, "assignments at least as dark as observed", note),
        "date_shuffle_block_count": (int(valid.sum()), "250 m blocks", note),
        "date_shuffle_reconstruction_max_error": (max_abs_error, "dB", note),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stacks", required=True, type=Path)
    parser.add_argument("--layers", required=True, type=Path)
    parser.add_argument("--site", required=True)
    parser.add_argument("--track", required=True)
    args = parser.parse_args()
    print(json.dumps({key: {"value": value, "unit": unit, "note": note}
                      for key, (value, unit, note) in calculate(args.stacks, args.layers, args.site, args.track).items()},
                     indent=2))


if __name__ == "__main__":
    main()
