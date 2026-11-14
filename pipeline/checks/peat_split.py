# Written with Super Intelligence (SI) assistance.
"""Split dry and fire detections on and off the official and CIFOR peat maps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

from pipeline.checks.common import read_grid, same_grid


def _area_km2(grid, count: int) -> float:
    """Area in km² from the affine pixel footprint and projected CRS units."""
    transform = grid.transform
    crs = grid.crs
    if crs is None or not crs.is_projected:
        raise ValueError("area calculation requires a projected raster grid")
    if crs.linear_units.lower() not in {"metre", "meter"}:
        raise ValueError("area calculation requires a projected CRS measured in metres")
    pixel_m2 = abs(transform.a * transform.e - transform.b * transform.d)
    return float(count * pixel_m2 / 1_000_000)


def _read(path: Path):
    a, grid = read_grid(path)
    with rasterio.open(path) as src:
        tags = {str(k).lower(): str(v) for k, v in src.tags().items()}
        # Zero and one are valid classes, never nodata codes.
        if src.nodata in (0, 1):
            raise ValueError(f"{path.name}: nodata conflicts with valid 0/1 class values")
        raw = src.read(1, masked=False)
        available = src.dataset_mask() > 0
        if src.nodata is None and np.any((raw == 255) & available):
            raise ValueError(f"{path.name}: 255 appears to be nodata but is not declared as such")
    return np.asarray(a), grid, tags


def _split_metrics(prefix: str, signal: np.ndarray, peat: np.ndarray, grid, signal_name: str, source: str):
    out: dict[str, tuple[float | None, str, str]] = {}
    if not np.isfinite(signal).any():
        for part in ("on", "off"):
            out[f"{prefix}_{part}_km2"] = (None, "km²", f"No valid {signal_name} data")
            out[f"{prefix}_{part}_share"] = (None, "share", f"No valid {signal_name} data")
            out[f"{prefix}_{part}_valid_km2"] = (None, "km²", f"No valid {signal_name} data")
        out[f"{prefix}_unknown_valid_km2"] = (None, "km²", f"No valid {signal_name} data")
        return out
    signal_valid = np.isfinite(signal)
    signal_on = signal_valid & (signal > 0)
    unknown = signal_valid & ~np.isfinite(peat)
    out[f"{prefix}_unknown_valid_km2"] = (
        _area_km2(grid, int(unknown.sum())), "km²",
        f"Valid {signal_name} footprint without mapped peat coverage; excluded from both denominators; map source: {source}",
    )
    # Peat rasters are binary with nodata represented as NaN. Explicit zero is
    # off mapped peat; missing peat coverage is never counted as off peat.
    for part, peat_value in (("on", True), ("off", False)):
        valid = signal_valid & np.isfinite(peat) & ((peat > 0) == peat_value)
        valid_n = int(valid.sum())
        signal_n = int((valid & signal_on).sum())
        out[f"{prefix}_{part}_km2"] = (_area_km2(grid, signal_n) if valid_n else None, "km²", f"{signal_name} area {part} mapped peat; map source: {source}")
        out[f"{prefix}_{part}_share"] = (
            float(signal_n / valid_n) if valid_n else None,
            "share",
            f"{signal_name} share of valid area {part} mapped peat; map source: {source}" if valid_n else f"No valid {part}-peat coverage; map source: {source}",
        )
        out[f"{prefix}_{part}_valid_km2"] = (_area_km2(grid, valid_n), "km²", f"Valid {signal_name} coverage {part} mapped peat; map source: {source}")
    return out


def calculate(layers: Path, site: str) -> dict[str, tuple[float | None, str, str]]:
    """Return dry/fire areas and shares split by each available peat map.

    ``dried_<site>.tif`` is required. Fire is included when present but its
    absence does not suppress dry-area reporting. Missing peat layers produce
    explicit no-data metrics instead of treating unmapped cells as non-peat.
    """
    dry_path = layers / f"dried_{site}.tif"
    if not dry_path.is_file():
        raise ValueError(f"missing dry mask: {dry_path}")
    dry, grid, dry_tags = _read(dry_path)
    if not grid.crs or not grid.crs.is_projected:
        raise ValueError("dry-mask grid must use a projected CRS for area reporting")
    if dry_tags.get("units") not in (None, "", "class", "binary", "1"):
        raise ValueError("dry mask has unexpected units; expected a binary class layer")
    if dry_tags.get("layer") != "dried on both orbits":
        raise ValueError("dry mask is missing its both-orbit product label")
    for track in ("061", "125"):
        try:
            floor = float(dry_tags[f"floor_{track}"])
        except (KeyError, ValueError) as exc:
            raise ValueError(f"dry mask is missing a valid track-{track} noise-floor tag") from exc
        if not np.isfinite(floor) or floor > 0:
            raise ValueError(f"dry mask has an invalid track-{track} noise-floor value")
    if np.isfinite(dry).any() and not np.isin(np.unique(dry[np.isfinite(dry)]), [0, 1]).all():
        raise ValueError("dry mask must contain only 0 and 1 values")

    fire_path = layers / f"fire_days_{site}.tif"
    fire = None
    fire_grid = None
    if fire_path.is_file():
        fire, fire_grid, _ = _read(fire_path)
        same_grid(grid, fire_grid)
        days = fire[np.isfinite(fire)]
        if np.any(days < 0) or np.any(days != np.floor(days)):
            raise ValueError("fire_days must contain nonnegative integer counts or nodata")

    out: dict[str, tuple[float | None, str, str]] = {}
    for map_name in ("official", "cifor", "peatmap"):
        peat_path = layers / f"peat_{map_name}_{site}.tif"
        prefix = f"peat_{map_name}"
        if not peat_path.is_file():
            for signal_name in ("dried", "fire"):
                for part in ("on", "off"):
                    out[f"{signal_name}_{prefix}_{part}_km2"] = (None, "km²", f"Missing peat map: {peat_path.name}")
                    out[f"{signal_name}_{prefix}_{part}_share"] = (None, "share", f"Missing peat map: {peat_path.name}")
                    out[f"{signal_name}_{prefix}_{part}_valid_km2"] = (None, "km²", f"Missing peat map: {peat_path.name}")
            continue
        peat, peat_grid, peat_tags = _read(peat_path)
        same_grid(grid, peat_grid)
        if peat_tags.get("units") not in (None, "", "class", "binary", "1"):
            raise ValueError(f"{peat_path.name} has unexpected units; expected a binary mask")
        if np.isfinite(peat).any() and not np.isin(np.unique(peat[np.isfinite(peat)]), [0, 1]).all():
            raise ValueError(f"{peat_path.name} must contain only 0 and 1 values")
        source = peat_tags.get("source") or peat_tags.get("citation") or "source not recorded in GeoTIFF tags"
        out.update(_split_metrics(f"dried_peat_{map_name}", dry, peat, grid, "dried area", source))
        if fire is not None:
            # Convert positive detections to a binary presence mask; zero fire
            # days is valid and remains in the denominator.
            fire_binary = np.where(np.isfinite(fire), (fire > 0).astype("float32"), np.nan)
            out.update(_split_metrics(f"fire_peat_{map_name}", fire_binary, peat, grid, "fire-detected area", source))
        else:
            for part in ("on", "off"):
                out[f"fire_peat_{map_name}_{part}_km2"] = (None, "km²", "Fire layer missing; dry-area split is still available")
                out[f"fire_peat_{map_name}_{part}_share"] = (None, "share", "Fire layer missing; dry-area split is still available")
                out[f"fire_peat_{map_name}_{part}_valid_km2"] = (None, "km²", "Fire layer missing; dry-area split is still available")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layers", type=Path, required=True)
    parser.add_argument("--site", required=True)
    args = parser.parse_args()
    result = calculate(args.layers, args.site)
    print(json.dumps({k: {"value": v, "unit": u, "note": n} for k, (v, u, n) in result.items()}, indent=2))


if __name__ == "__main__":
    main()
