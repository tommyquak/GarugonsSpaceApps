# Written with Super Intelligence (SI) assistance.
"""Checks on the drying layers themselves: do they survive choices we made and artefacts we could have introduced?

  A  overlap      the west and east boxes overlap in a strip; the same ground must score the same in both
  B  reference    the per-date offsets must not depend on how the reference forest is drawn
  C  tilt         the score must not slope across the swath (a sign of a geometry artefact)
  D  alignment    the two orbits must be registered to each other after regridding
  E  season       dried land should darken through the dry season and brighten after the rain; forest should not

Prints a report and writes the numbers to validation.json.

    python pipeline/drying/selfcheck.py --stacks pipeline/out/stacks --layers pipeline/out/layers --dry-until 20261025
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from baseline import REFERENCE, reference_mask  # noqa: E402
from common import block_mean, load_stack, lonlat  # noqa: E402
from vjson import put  # noqa: E402

ME = "pipeline/drying/selfcheck.py"


def read(path):
    with rasterio.open(path) as src:
        return src.read(1), src.transform, src.crs


def check_overlap(layers, tracks):
    out = {}
    for t in tracks:
        w, Tw, crs = read(layers / f"drydown_west_{t}.tif")
        e, Te, _ = read(layers / f"drydown_east_{t}.tif")
        e_on_w = np.full(w.shape, np.nan, "float32")
        reproject(e, e_on_w, src_transform=Te, src_crs=crs, src_nodata=np.nan, dst_transform=Tw, dst_crs=crs,
                  dst_nodata=np.nan, resampling=Resampling.bilinear)
        k = np.isfinite(w) & np.isfinite(e_on_w)
        d = (w - e_on_w)[k]
        out[t] = {"km2": round(float(k.sum() * 0.0025), 0), "r": float(np.corrcoef(w[k], e_on_w[k])[0, 1]),
                  "mean_diff_db": float(d.mean()), "p95_abs_diff_db": float(np.percentile(np.abs(d), 95))}
        put(f"selfcheck_overlap_r_{t}", out[t]["r"], "Pearson r", "west and east", ME, note=f"same ground in both boxes, {out[t]['km2']:.0f} km2")
        put(f"selfcheck_overlap_p95_abs_diff_{t}", out[t]["p95_abs_diff_db"], "dB", "west and east", ME)
    return out


def check_reference(stacks, tracks):
    out = {}
    for t in tracks:
        s = load_stack(stacks / f"west_{t}.npz")
        ref, box = reference_mask(s)
        lon, lat = lonlat(s)
        hv = np.nanmean(s["hv"], axis=0)
        mid_lat = (REFERENCE["bbox"][1] + REFERENCE["bbox"][3]) / 2
        variants = {"default (brighter half in HV)": ref, "brightest quarter in HV": box & (hv > np.nanpercentile(hv[box], 75)),
                    "whole box": box, "north half of the reference": ref & (lat > mid_lat), "south half of the reference": ref & (lat <= mid_lat)}
        offs = {}
        for name, m in variants.items():
            med = np.array([np.nanmedian(layer[m]) for layer in s["hh"]])
            offs[name] = med - med.mean()
        worst = {name: float(np.max(np.abs(o - offs["default (brighter half in HV)"]))) for name, o in offs.items()}
        out[t] = {k: round(v, 3) for k, v in worst.items()}
        put(f"selfcheck_reference_max_offset_shift_{t}", max(worst.values()), "dB", "west", ME,
            note="largest change in any date's offset across five ways of drawing the reference forest")
    return out


def check_tilt(stacks, layers, tracks):
    out = {}
    for t in tracks:
        s = load_stack(stacks / f"west_{t}.npz")
        ref, _ = reference_mask(s)
        score, _, _ = read(layers / f"drydown_west_{t}.tif")
        rows, cols = score.shape
        east_km = np.tile(np.arange(cols) * 0.05, (rows, 1))
        north_km = np.tile(-np.arange(rows)[:, None] * 0.05, (1, cols))
        k = ref & np.isfinite(score)
        A = np.c_[east_km[k], north_km[k], np.ones(k.sum())]
        coef = np.linalg.lstsq(A, score[k], rcond=None)[0]
        out[t] = {"east_db_per_10km": float(coef[0] * 10), "north_db_per_10km": float(coef[1] * 10),
                  "reference_width_km": float(np.ptp(east_km[k])), "reference_height_km": float(np.ptp(north_km[k]))}
        put(f"selfcheck_tilt_east_{t}", out[t]["east_db_per_10km"], "dB per 10 km", "west", ME, note="slope of the score across the reference forest, west to east")
        put(f"selfcheck_tilt_north_{t}", out[t]["north_db_per_10km"], "dB per 10 km", "west", ME)
    return out


def check_alignment(stacks, tracks, site="west", reach=3):
    a = np.nanmean(load_stack(stacks / f"{site}_{tracks[0]}.npz")["hh"], axis=0)
    b = np.nanmean(load_stack(stacks / f"{site}_{tracks[1]}.npz")["hh"], axis=0)
    best, table = None, {}
    core = (slice(reach, -reach), slice(reach, -reach))
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            shifted = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
            k = np.isfinite(a[core]) & np.isfinite(shifted[core])
            r = float(np.corrcoef(a[core][k][::5], shifted[core][k][::5])[0, 1])
            table[(dy, dx)] = r
            if best is None or r > table[best]:
                best = (dy, dx)
    put(f"selfcheck_orbit_alignment_best_shift_{site}", f"{best[0]},{best[1]}", "pixels (rows, cols)", site, ME,
        note="shift of the descending image that best matches the ascending one; 0,0 means registered")
    return {"best_shift_rows_cols": best, "r_at_zero": table[(0, 0)], "r_at_best": table[best], "r_one_pixel_off": max(table[(0, 1)], table[(1, 0)], table[(0, -1)], table[(-1, 0)])}


def check_season(stacks, layers, tracks, dry_until):
    out = {}
    for t in tracks:
        s = load_stack(stacks / f"west_{t}.npz")
        base = json.loads((layers / f"baseline_{t}.json").read_text())
        dried, _, _ = read(layers / "dried_west.tif")
        score, _, _ = read(layers / f"drydown_west_{t}.tif")
        ref, _ = reference_mask(s)
        strong = (dried == 1) & (score < -1.0)
        off = np.array(base["hh"]["offset_db"])
        series = {"dried by 1 dB or more": [float(np.nanmedian(layer[strong]) - o) for layer, o in zip(s["hh"], off)],
                  "reference forest": [float(np.nanmedian(layer[ref]) - o) for layer, o in zip(s["hh"], off)]}
        rel = [round(v - series["dried by 1 dB or more"][0], 2) for v in series["dried by 1 dB or more"]]
        after = [d for d in s["dates"] if d > dry_until]
        out[t] = {"dates": [d[4:] for d in s["dates"]], "dried_land_hh_relative_to_first_pass_db": rel,
                  "reference_relative_db": [round(v - series["reference forest"][0], 2) for v in series["reference forest"]],
                  "passes_after_rain": [d[4:] for d in after]}
        if after:
            i = s["dates"].index(after[0])
            put(f"selfcheck_rebound_after_rain_{t}", float(rel[i] - rel[i - 1]), "dB", "west", ME,
                note=f"change in HH of strongly dried land from the last dry pass to {after[0]}")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--tracks", nargs=2, default=["125", "061"])
    p.add_argument("--dry-until", required=True)
    a = p.parse_args()
    report = {"A_overlap": check_overlap(a.layers, a.tracks), "B_reference": check_reference(a.stacks, a.tracks),
              "C_tilt": check_tilt(a.stacks, a.layers, a.tracks), "D_alignment": check_alignment(a.stacks, a.tracks),
              "E_season": check_season(a.stacks, a.layers, a.tracks, a.dry_until)}
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()
