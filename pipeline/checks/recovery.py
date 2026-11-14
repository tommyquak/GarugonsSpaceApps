# Written with Super Intelligence (SI) assistance.
"""Check first-rain radar response against the other orbit's dry-down.

The recovery files are ``recovery_{hh,hv}_<site>_<orbit>.tif``. They must
retain the source track and exact pass dates in tags or in a neighbouring
``.tif.json`` sidecar. Where rainfall has not been independently confirmed,
the returned metrics are labelled exploratory.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import uniform_filter
from scipy.stats import spearmanr

from pipeline.checks.common import centres, read_drydown, read_grid, same_grid


def _iso(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"expected ISO date YYYY-MM-DD, got {value!r}") from exc


def _metadata(path: Path) -> dict[str, str]:
    with rasterio.open(path) as src:
        tags = {str(k).lower(): str(v) for k, v in src.tags().items()}
    sidecar = path.with_suffix(path.suffix + ".json")
    if sidecar.is_file():
        sidecar_data = json.loads(sidecar.read_text())
        if not isinstance(sidecar_data, dict):
            raise ValueError(f"invalid provenance sidecar: {sidecar}")
        sidecar_tags = {str(k).lower(): str(v) for k, v in sidecar_data.items()}
        for key, value in sidecar_tags.items():
            if key in tags and tags[key] != value:
                raise ValueError(f"{path.name}: sidecar conflicts with embedded TIFF tag {key!r}")
        for key, value in sidecar_tags.items():
            tags.setdefault(key, value)
    return tags


def _check_provenance(path: Path, pol: str, orbit: str, rain_date: str | None) -> tuple[tuple[str, str], str]:
    meta = _metadata(path)
    track = meta.get("track", meta.get("orbit"))
    pol_tag = meta.get("polarization", meta.get("pol"))
    before = meta.get("late_passes", meta.get("pre_date", meta.get("before_date")))
    after = meta.get("post_date", meta.get("after_date", meta.get("after_pass")))
    if track != orbit:
        raise ValueError(f"{path.name}: missing or incorrect track {orbit} provenance")
    if pol_tag and pol_tag.lower() != pol:
        raise ValueError(f"{path.name}: polarization provenance does not match {pol}")
    layer = meta.get("layer", "").lower()
    if pol.lower() not in layer or "rebound" not in layer:
        raise ValueError(f"{path.name}: layer tag must identify {pol.upper()} rebound")
    if meta.get("units", "").lower() != "db":
        raise ValueError(f"{path.name}: recovery units must be explicitly tagged dB")
    if not before or not after:
        raise ValueError(f"{path.name}: exact late_passes and after_pass provenance is required")
    late = tuple(d.strip().replace("-", "") for d in before.split(",") if d.strip())
    after_dates = tuple(d.strip().replace("-", "") for d in after.split(",") if d.strip())
    dates = (*late, *after_dates)
    if len(late) != 2 or len(set(late)) != 2 or len(after_dates) != 1 or any(len(d) != 8 or not d.isdigit() for d in dates):
        raise ValueError(f"{path.name}: invalid acquisition dates in provenance")
    for acquisition in dates:
        _iso(f"{acquisition[:4]}-{acquisition[4:6]}-{acquisition[6:]}")
    if late != tuple(sorted(late)) or not late[0] < late[1] < after_dates[0]:
        raise ValueError(f"{path.name}: late passes must be two distinct ordered dates before after_pass")
    if rain_date:
        rain = _iso(rain_date).strftime("%Y%m%d")
        if not late[1] < rain < after_dates[0]:
            raise ValueError(f"{path.name}: rain onset is not bracketed by the source acquisitions")
    return (late[0], late[1]), after_dates[0]


def calculate(
    layers: Path,
    site: str,
    orbit: str,
    rain_date: str | None = None,
    recovery_dir: Path | None = None,
) -> dict[str, tuple[float | int | None, str, str]]:
    """Return recovery metrics, keyed by suffix, as ``(value, unit, note)``.

    `orbit` is 061 or 125. The selected orbit's HH/HV response is paired with
    the opposite orbit's independently computed dry-down. A supplied rain
    date is checked against both acquisition windows; a positive daily total
    is reported as evidence on that date, not as proof that it was the onset.
    """
    if orbit not in {"061", "125"}:
        raise ValueError("orbit must be 061 or 125")
    if rain_date:
        _iso(rain_date)
    other_orbit = "125" if orbit == "061" else "061"
    source_dir = recovery_dir or layers
    positive_rain_total: float | None = None
    if rain_date:
        rain_path = layers / f"rain_daily_{site}.json"
        if rain_path.is_file():
            record = json.loads(rain_path.read_text())
            rain_mm = record.get(rain_date) if isinstance(record, dict) else None
            if type(rain_mm) not in (int, float) or not np.isfinite(rain_mm) or rain_mm <= 0:
                raise ValueError(f"rainfall on onset date {rain_date} is absent or not positive")
            positive_rain_total = float(rain_mm)

    out: dict[str, tuple[float | int | None, str, str]] = {}
    source_dates: tuple[tuple[str, str], str] | None = None
    windows: dict[str, tuple[tuple[str, str], str]] = {}
    drydowns: dict[str, np.ndarray] = {}
    drydown_grids = {}
    for track in (orbit, other_orbit):
        values, grid, tags = read_drydown(layers, site, track)
        windows[track] = (tuple(tags["late_passes"].split(",")), tags["dry_until"])
        drydowns[track] = values
        drydown_grids[track] = grid
    own_late, own_cutoff = windows[orbit]
    other_late, other_cutoff = windows[other_orbit]
    if own_cutoff != other_cutoff:
        raise ValueError("opposite-orbit dry-downs use different dry-until cutoffs")
    # The recovery raster is built from these exact two dry passes. The other
    # orbit is a separate acquisition window, but its last dry observation
    # must still predate this orbit's response pass and any supplied onset.
    same_grid(drydown_grids[orbit], drydown_grids[other_orbit])
    responses = {}
    response_grids = {}
    for pol in ("hh", "hv"):
        recovery_path = source_dir / f"recovery_{pol}_{site}_{orbit}.tif"
        drydown_path = layers / f"drydown_{site}_{other_orbit}.tif"
        if not recovery_path.is_file() or not drydown_path.is_file():
            raise ValueError(f"missing {pol.upper()} track-{orbit} recovery or track-{other_orbit} dry-down raster")
        before, after = _check_provenance(recovery_path, pol, orbit, rain_date)
        if before != own_late:
            raise ValueError(f"{recovery_path.name}: recovery late passes do not match the {orbit} dry-down window")
        if after <= own_cutoff:
            raise ValueError(f"{recovery_path.name}: response pass is not after the shared dry-until cutoff")
        if other_late[-1] >= after:
            raise ValueError(f"track-{other_orbit} dry window does not precede the response pass")
        if rain_date and other_late[-1] >= _iso(rain_date).strftime("%Y%m%d"):
            raise ValueError(f"track-{other_orbit} last dry acquisition is not before supplied rain date")
        if source_dates is not None and source_dates != (before, after):
            raise ValueError("HH and HV recovery layers do not use the same exact acquisitions")
        source_dates = (before, after)
        recovery, recovery_grid = read_grid(recovery_path)
        responses[pol] = np.asarray(centres(recovery), dtype="float64").ravel()
        response_grids[pol] = recovery_grid
        drydown = drydowns[other_orbit]
        drydown_grid = drydown_grids[other_orbit]
        same_grid(recovery_grid, drydown_grid)
    same_grid(response_grids["hh"], response_grids["hv"], drydown_grids[other_orbit])
    dry = np.asarray(centres(drydowns[other_orbit]), dtype="float64").ravel()
    valid = np.isfinite(responses["hh"]) & np.isfinite(responses["hv"]) & np.isfinite(dry)
    if valid.sum() < 20:
        raise ValueError(f"too few HH/HV/opposite-orbit paired valid centres ({int(valid.sum())})")
    dry_strength = -dry[valid]
    cohort_n = max(1, dry_strength.size // 10)
    driest = np.argsort(-dry_strength, kind="stable")[:cohort_n]
    detail = (f"Recovery passes {','.join(source_dates[0])} then {source_dates[1]}; "
              f"comparison track-{other_orbit} dry-down passes {','.join(other_late)}; ")
    if positive_rain_total is not None:
        status = (f"positive daily total {positive_rain_total:g} mm on supplied date {rain_date}; "
                  "this does not by itself establish the onset")
    elif rain_date:
        status = f"supplied date {rain_date} has no locally available daily rainfall evidence; exploratory"
    else:
        status = "rainfall onset date not supplied; exploratory"
    detail += status
    for pol in ("hh", "hv"):
        response = responses[pol][valid]
        # Dry-down is negative when the surface darkened; negate it so larger
        # values represent a stronger independent dry-season signal.
        rho = float(spearmanr(response, dry_strength).statistic)
        if not np.isfinite(rho):
            raise ValueError(f"{pol.upper()} response association is undefined")
        prefix = f"recovery_{orbit}_{pol}"
        out[f"{prefix}_paired_n"] = (int(response.size), "250 m blocks", "Paired valid centres; " + detail)
        out[f"{prefix}_median_db"] = (float(np.median(response)), "dB", "Median response across source passes; " + detail)
        out[f"{prefix}_drydown_spearman_r"] = (rho, "Spearman r", f"Association with negative track-{other_orbit} dry-down; " + detail)
        out[f"{prefix}_driest_decile_n"] = (cohort_n, "250 m blocks", f"Floor(n/10) strongest track-{other_orbit} dry-down centres; ties break row-major")
        out[f"{prefix}_driest_decile_median_db"] = (float(np.median(response[driest])), "dB", f"Median response among strongest track-{other_orbit} dry-down decile; " + detail)
    return out


def audit_hv_absolute(
    stacks: Path,
    layers: Path,
    site: str,
    orbit: str,
    recovery_dir: Path | None = None,
    tolerance_db: float = 0.005,
) -> dict[str, object]:
    """Rebuild released HV rebound as measured and identify affected values.

    This is deliberately best-effort for historical releases: if the supplied
    stack lacks any tagged acquisition or does not share the release grid, the
    result says ``available=False`` and holds nothing. A global baseline shift
    changes absolute medians while leaving the ranks, counts and cohort intact.
    """
    if orbit not in {"061", "125"}:
        raise ValueError("orbit must be 061 or 125")
    if not np.isfinite(tolerance_db) or tolerance_db < 0:
        raise ValueError("tolerance_db must be finite and nonnegative")

    source_dir = recovery_dir or layers
    hv_path = source_dir / f"recovery_hv_{site}_{orbit}.tif"
    hh_path = source_dir / f"recovery_hh_{site}_{orbit}.tif"
    stack_path = stacks / f"{site}_{orbit}.npz"
    empty = {"available": False, "hold_suffixes": [], "reason": ""}
    if not stack_path.is_file() or not hv_path.is_file() or not hh_path.is_file():
        empty["reason"] = "matching stack or recovery files are unavailable"
        return empty

    late, after = _check_provenance(hv_path, "hv", orbit, None)
    hh_late, hh_after = _check_provenance(hh_path, "hh", orbit, None)
    if (late, after) != (hh_late, hh_after):
        raise ValueError("HH and HV recovery layers do not use the same exact acquisitions")
    with np.load(stack_path) as saved:
        stack = {
            "hv": saved["hv"].astype("float32"),
            "cov": saved["cov"].astype(bool),
            "T": rasterio.Affine(*saved["T"]),
            "epsg": int(saved["crs"]),
            "dates": [str(day) for day in saved["dates"]],
        }
    indices = {day: i for i, day in enumerate(stack["dates"])}
    required_dates = (*late, after)
    if len(indices) != len(stack["dates"]) or any(day not in indices for day in required_dates):
        empty["reason"] = "the stack does not contain every tagged late and response acquisition"
        return empty

    hv, hv_grid = read_grid(hv_path)
    hh, hh_grid = read_grid(hh_path)
    other_orbit = "125" if orbit == "061" else "061"
    other_dry, dry_grid, _ = read_drydown(layers, site, other_orbit)
    same_grid(hv_grid, hh_grid, dry_grid)
    with rasterio.open(hv_path) as src:
        stack_grid_matches = (
            src.shape == stack["cov"].shape
            and src.transform == stack["T"]
            and src.crs is not None
            and src.crs.to_epsg() == stack["epsg"]
        )
    if not stack_grid_matches:
        empty["reason"] = "the matching stack and recovery rasters are on different grids"
        return empty

    hv_layers = stack["hv"]
    def smooth(values: np.ndarray) -> np.ndarray:
        have_data = np.isfinite(values).astype("float32")
        totals = uniform_filter(np.nan_to_num(values), size=5, mode="nearest")
        coverage = uniform_filter(have_data, size=5, mode="nearest")
        return np.where(coverage > 0.5, totals / np.maximum(coverage, 1e-6), np.nan)

    late_values = [smooth(hv_layers[indices[day]]) for day in late]
    rebound = smooth(hv_layers[indices[after]]) - np.mean(late_values, axis=0)
    rebound[~stack["cov"]] = np.nan
    expected = centres(rebound).ravel()
    released = centres(hv).ravel()
    hh_centres = centres(hh).ravel()
    dry_centres = centres(other_dry).ravel()
    base = np.isfinite(hh_centres) & np.isfinite(dry_centres)
    if not np.array_equal(np.isfinite(expected)[base], np.isfinite(released)[base]):
        empty["reason"] = "reconstructed and released HV valid coverage differs on the HH/dry-down cohort"
        empty["unverified_suffixes"] = [
            f"recovery_{orbit}_hv_median_db",
            f"recovery_{orbit}_hv_driest_decile_median_db",
            f"recovery_{orbit}_hv_drydown_spearman_r",
        ]
        return empty
    paired = base & np.isfinite(expected) & np.isfinite(released)
    n = int(paired.sum())
    if n < 20:
        empty["reason"] = f"too few shared valid centres to compare ({n})"
        return empty

    expected_values, released_values = expected[paired], released[paired]
    dry_strength = -dry_centres[paired]
    cohort_n = max(1, dry_strength.size // 10)
    cohort = np.argsort(-dry_strength, kind="stable")[:cohort_n]
    expected_median = float(np.median(expected_values))
    released_median = float(np.median(released_values))
    expected_cohort_median = float(np.median(expected_values[cohort]))
    released_cohort_median = float(np.median(released_values[cohort]))
    residual = released_values - expected_values
    expected_r = float(spearmanr(expected_values, dry_strength).statistic)
    released_r = float(spearmanr(released_values, dry_strength).statistic)
    rank_preserved = np.isfinite(expected_r) and np.isfinite(released_r) and round(expected_r, 4) == round(released_r, 4)
    uniform_shift = float(np.percentile(np.abs(residual - np.median(residual)), 95)) <= tolerance_db

    hold = []
    if abs(released_median - expected_median) > tolerance_db:
        hold.append(f"recovery_{orbit}_hv_median_db")
    if abs(released_cohort_median - expected_cohort_median) > tolerance_db:
        hold.append(f"recovery_{orbit}_hv_driest_decile_median_db")
    if not rank_preserved:
        hold.append(f"recovery_{orbit}_hv_drydown_spearman_r")
    note = (
        f"HV as measured from {','.join(late)} then {after}; {n} shared valid centres; "
        f"released minus reconstructed medians {released_median - expected_median:+.4f} dB overall and "
        f"{released_cohort_median - expected_cohort_median:+.4f} dB in the strongest-decile cohort."
    )
    if uniform_shift and rank_preserved:
        note += " Difference is an approximately uniform offset; ranks and cohort membership are preserved."
    return {
        "available": True,
        "hold_suffixes": hold,
        "shared_blocks": n,
        "driest_decile_blocks": cohort_n,
        "released_median_db": released_median,
        "reconstructed_median_db": expected_median,
        "released_driest_decile_median_db": released_cohort_median,
        "reconstructed_driest_decile_median_db": expected_cohort_median,
        "median_delta_db": released_median - expected_median,
        "driest_decile_median_delta_db": released_cohort_median - expected_cohort_median,
        "rank_preserved": bool(rank_preserved),
        "reconstructed_drydown_spearman_r": expected_r,
        "released_drydown_spearman_r": released_r,
        "uniform_shift": uniform_shift,
        "note": note,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layers", type=Path, required=True, help="directory containing drydown layers and optional rain JSON")
    parser.add_argument("--recovery-dir", type=Path, help="directory containing orbit-keyed recovery rasters")
    parser.add_argument("--site", required=True)
    parser.add_argument("--orbit", required=True, choices=("061", "125"))
    parser.add_argument("--rain-date", help="optional onset date YYYY-MM-DD, checked when a positive rainfall record is available")
    args = parser.parse_args()
    result = calculate(args.layers, args.site, args.orbit, args.rain_date, args.recovery_dir)
    print(json.dumps({k: {"value": v, "unit": u, "note": n} for k, (v, u, n) in result.items()}, indent=2))


if __name__ == "__main__":
    main()
