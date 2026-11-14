# Written with Super Intelligence (SI) assistance.
"""Turns pipeline GeoTIFFs into the images and lists the web map reads.

Reads the layers of docs/DATA_CONTRACT.md section 2 and writes, under the output folder:

    layers/<id>.png      one image per layer, warped to Web Mercator (EPSG:3857)
    layers/layers.json   the list the app reads (contract section 5)
    series/              the click-chart files of contract section 4, copied as they are,
                         plus index.json naming what is there
    validation.json      the numbers file, copied as it is

Run from the repo root:

    python3 app/scripts/make_layers.py --layers pipeline/out/layers --out app/public

Layers written, each only if its input exists:

    dried_<site>                    mean dry-season fall in HH of the two orbits, where the block
                                    dried beyond the noise floor on both (dried_<site>.tif)
    hh_<site>_<track>_<YYYYMMDD>    one per radar pass, fall in HH against the start of the season
    reference_<site>                the intact reference forest, as an outline with a light fill
    fire_<site>                     land with at least one fire detection day (fire_days_<site>.tif)
    recovery_hh_<site>              rise in HH across the first rain, mean of the orbits, in a blue ramp

A fall is drawn from --min-db upward and reaches the end of the ramp at --full-db. Smaller falls
and cells with no data are transparent. The ramp is the one of pipeline/drying/one_look_map.py.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import array_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

# Same colours and full scale as pipeline/drying/one_look_map.py (RAMP, FULL_SCALE_DB).
RAMP = ["#f6e27a", "#f0a04b", "#d9502e", "#8f1d1d", "#4a0d12"]
FULL_SCALE_DB = 3.0
RAMP_RISE = ["#d6ecff", "#8cc5f2", "#3f97d9", "#1f5fa8", "#12305e"]  # light to deep blue, for a rise
MIN_DB = 1.0
LEVELS = 48  # colour steps between --min-db and --full-db

SOURCE_RADAR = "NISAR L2 GCOV, ASF DAAC"
SOURCE_FIRE = "NASA FIRMS active fire detections"
REFERENCE_RGB = (159, 214, 184)
FIRE_RGB = (8, 8, 10)


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def ramp_rgb(t, colors):
    """Colour of a ramp at t in 0..1, linear between evenly spaced stops."""
    stops = np.array([hex_rgb(h) for h in colors], dtype=float)
    x = np.clip(t, 0, 1) * (len(stops) - 1)
    i = np.minimum(x.astype(int), len(stops) - 2)
    f = (x - i)[..., None]
    return np.round(stops[i] * (1 - f) + stops[i + 1] * f).astype(np.uint8)


class Grid:
    """The Web Mercator grid of one site at one pixel size."""

    def __init__(self, src, res):
        self.src_crs, self.src_transform, self.src_shape = src.crs, src.transform, src.shape
        self.transform, self.width, self.height = calculate_default_transform(
            src.crs, "EPSG:3857", src.width, src.height, *src.bounds, resolution=res)
        west, south, east, north = array_bounds(self.height, self.width, self.transform)
        # A Web Mercator rectangle is also a rectangle in longitude and latitude.
        self.bounds = [round(v, 6) for v in transform_bounds("EPSG:3857", "EPSG:4326", west, south, east, north)]

    def fits(self, src):
        return src.crs == self.src_crs and src.transform == self.src_transform and src.shape == self.src_shape

    def warp(self, data, resampling):
        out = np.full((self.height, self.width), np.nan, dtype=np.float32)
        reproject(data.astype(np.float32), out, src_transform=self.src_transform, src_crs=self.src_crs,
                  src_nodata=np.nan, dst_transform=self.transform, dst_crs="EPSG:3857", dst_nodata=np.nan,
                  resampling=resampling)
        return out


class Grids:
    """One grid per site and pixel size, so every image of a site has the same corners."""

    def __init__(self):
        self.made = {}

    def get(self, site, path, res):
        with rasterio.open(path) as src:
            data = src.read(1)
            grid = self.made.get((site, res))
            if grid is None or not grid.fits(src):
                grid = Grid(src, res)
                self.made.setdefault((site, res), grid)
        return data, grid


def save_palette(path, index, palette_rgb, alpha):
    """Write an 8-bit palette PNG. index 0 is always fully transparent."""
    img = Image.fromarray(index.astype(np.uint8), mode="P")
    flat = np.zeros((256, 3), dtype=np.uint8)
    flat[:len(palette_rgb)] = palette_rgb
    img.putpalette(flat.tobytes())
    img.save(path, optimize=True, transparency=bytes(alpha))


def save_fall(path, fall, show, min_db, full_db, colors=RAMP):
    """Colour a change in decibels with a ramp. Index 0 is transparent."""
    step = np.round((np.clip(fall, min_db, full_db) - min_db) / (full_db - min_db) * (LEVELS - 1))
    index = np.where(show, 1 + np.nan_to_num(step), 0)
    levels = min_db + (full_db - min_db) * np.arange(LEVELS) / (LEVELS - 1)
    palette = np.vstack([[0, 0, 0], ramp_rgb(levels / FULL_SCALE_DB, colors)])
    save_palette(path, index, palette, [0] + [255] * LEVELS)


def save_mask(path, mask, rgb, fill_alpha, edge_alpha, edge_px):
    """Draw a yes or no layer as a light fill with a stronger outline."""
    inside = mask.copy()
    for _ in range(edge_px):
        p = np.pad(inside, 1, constant_values=False)
        inside = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    index = np.where(mask, np.where(inside, 1, 2), 0)
    save_palette(path, index, [(0, 0, 0), rgb, rgb], [0, fill_alpha, edge_alpha])


def ramp_entry(min_db, full_db, colors=RAMP, title="Fall in HH brightness"):
    return {"title": title, "colors": colors, "scale": [0.0, FULL_SCALE_DB], "shown_from": min_db, "full_at": full_db}


def iso(yyyymmdd):
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--layers", required=True, type=Path, help="folder with the pipeline GeoTIFFs")
    p.add_argument("--out", required=True, type=Path, help="the app's public folder")
    p.add_argument("--series", type=Path, help="folder with series_<site>.json and .bin (default: next to --layers)")
    p.add_argument("--validation", type=Path, help="validation.json (default: next to --layers)")
    p.add_argument("--min-db", type=float, default=MIN_DB, help="smallest fall that is drawn")
    p.add_argument("--full-db", type=float, default=FULL_SCALE_DB, help="fall drawn in the last colour")
    p.add_argument("--res", type=float, default=50.0, help="pixel size of the whole-season images, metres")
    p.add_argument("--pass-res", type=float, default=100.0, help="pixel size of the per-pass images, metres")
    p.add_argument("--orbits", nargs="*", default=["125=dawn", "061=dusk", "010=dawn", "119=dusk"],
                   help="time of day of each track, as track=word")
    a = p.parse_args()

    orbit = dict(item.split("=") for item in a.orbits)
    series_dir = a.series or a.layers.parent / "series"
    validation = a.validation or a.layers.parent / "validation.json"
    out_layers = a.out / "layers"
    out_layers.mkdir(parents=True, exist_ok=True)
    grids = Grids()
    entries, written = [], set()

    def add(layer_id, title, grid, **more):
        written.add(f"{layer_id}.png")
        entry = {"id": layer_id, "title": title, "url": f"layers/{layer_id}.png", "bounds": grid.bounds,
                 "date": None, "unit": "dB", "legend": "sequential", "source": SOURCE_RADAR}
        entry.update(more)
        entries.append(entry)
        return out_layers / f"{layer_id}.png"

    # (a) The one-look layer: mean fall of the two orbits where both went beyond the noise floor.
    for dried_path in sorted(a.layers.glob("dried_*.tif")):
        site = dried_path.stem.split("_", 1)[1]
        drydowns = sorted(a.layers.glob(f"drydown_{site}_*.tif"))
        if not drydowns:
            print(f"skip dried_{site}: no drydown_{site}_<track>.tif")
            continue
        dried, grid = grids.get(site, dried_path, a.res)
        fall = -np.mean([grids.get(site, d, a.res)[0] for d in drydowns], axis=0)
        fall_m = grid.warp(fall, Resampling.bilinear)
        dried_m = grid.warp(dried, Resampling.nearest)
        show = (dried_m == 1) & (fall_m >= a.min_db)
        path = add(f"dried_{site}", f"Dried over the season, {site}", grid, kind="season", site=site,
                   tracks=[d.stem.rsplit("_", 1)[1] for d in drydowns], ramp=ramp_entry(a.min_db, a.full_db))
        save_fall(path, fall_m, show, a.min_db, a.full_db)

    # (b) One image per radar pass.
    for hh_path in sorted(a.layers.glob("hh_*.tif")):
        m = re.fullmatch(r"hh_(.+)_(\d{3})_(\d{8})", hh_path.stem)
        if not m:
            print(f"skip {hh_path.name}: name is not hh_<site>_<track>_<YYYYMMDD>.tif")
            continue
        site, track, day = m.groups()
        change, grid = grids.get(site, hh_path, a.pass_res)
        fall_m = -grid.warp(change, Resampling.bilinear)
        show = fall_m >= a.min_db
        path = add(hh_path.stem, "Fall in HH since the start of the season", grid, kind="pass", site=site,
                   track=track, orbit=orbit.get(track), date=iso(day), ramp=ramp_entry(a.min_db, a.full_db))
        save_fall(path, fall_m, show, a.min_db, a.full_db)

    # The rise across the first rain, once track 2b has exported it. Positive means brighter.
    # Files are recovery_hh_<site>.tif or one per orbit, recovery_hh_<site>_<track>.tif; orbits are averaged.
    by_site = {}
    for rec_path in sorted(a.layers.glob("recovery_hh_*.tif")):
        m = re.fullmatch(r"recovery_hh_(.+?)(?:_(\d{3}))?", rec_path.stem)
        by_site.setdefault(m.group(1), []).append((rec_path, m.group(2)))
    for site, found in by_site.items():
        grid = grids.get(site, found[0][0], a.res)[1]
        rise = np.mean([grids.get(site, path, a.res)[0] for path, _ in found], axis=0)
        rise_m = grid.warp(rise, Resampling.bilinear)
        path = add(f"recovery_hh_{site}", f"Rise after the rain, {site}", grid, kind="recovery", site=site,
                   tracks=[t for _, t in found if t],
                   ramp=ramp_entry(a.min_db, a.full_db, RAMP_RISE, "Rise in HH after the rain"))
        save_fall(path, rise_m, rise_m >= a.min_db, a.min_db, a.full_db, RAMP_RISE)

    # (c) Yes or no layers: the reference forest, and fire days once track 3 has exported them.
    for ref_path in sorted(a.layers.glob("reference_*.tif")):
        site = ref_path.stem.split("_", 1)[1]
        ref, grid = grids.get(site, ref_path, a.res)
        path = add(f"reference_{site}", f"Reference forest, {site}", grid, kind="reference", site=site,
                   unit=None, legend="outline", color="#%02x%02x%02x" % REFERENCE_RGB)
        save_mask(path, grid.warp(ref, Resampling.nearest) == 1, REFERENCE_RGB, 40, 235, 2)
    for fire_path in sorted(a.layers.glob("fire_days_*.tif")):
        site = fire_path.stem.split("_", 2)[2]
        days, grid = grids.get(site, fire_path, a.res)
        path = add(f"fire_{site}", f"Fire detected this year, {site}", grid, kind="fire", site=site,
                   unit=None, legend="fill", color="#%02x%02x%02x" % FIRE_RGB, source=SOURCE_FIRE)
        save_mask(path, grid.warp(days, Resampling.nearest) >= 1, FIRE_RGB, 225, 255, 1)

    for stale in out_layers.glob("*.png"):
        if stale.name not in written:
            stale.unlink()
    (out_layers / "layers.json").write_text(json.dumps(entries, indent=1) + "\n")

    # Click-chart files, copied as they are, with an index of what is there.
    out_series = a.out / "series"
    out_series.mkdir(parents=True, exist_ok=True)
    index = {}
    for meta in sorted(series_dir.glob("series_*.json")) if series_dir.is_dir() else []:
        site = meta.stem.split("_", 1)[1]
        if not meta.with_suffix(".bin").exists():
            print(f"skip {meta.name}: no .bin next to it")
            continue
        shutil.copyfile(meta, out_series / meta.name)
        shutil.copyfile(meta.with_suffix(".bin"), out_series / f"series_{site}.bin")
        index[site] = {"series": f"series/{meta.name}", "bin": f"series/series_{site}.bin", "rain": None}
        rain = a.layers / f"rain_daily_{site}.json"
        if rain.exists():
            shutil.copyfile(rain, out_series / rain.name)
            index[site]["rain"] = f"series/{rain.name}"
    (out_series / "index.json").write_text(json.dumps(index, indent=1) + "\n")

    if validation.exists():
        shutil.copyfile(validation, a.out / "validation.json")

    total = sum(f.stat().st_size for f in a.out.rglob("*") if f.is_file())
    print(f"{len(entries)} layers, series for {sorted(index) or 'no site'}, "
          f"validation {'copied' if validation.exists() else 'missing'}, {total / 1e6:.1f} MB in {a.out}")
    for e in entries:
        if e["date"] is None:
            print(f"  {e['id']}: west {e['bounds'][0]}, south {e['bounds'][1]}, east {e['bounds'][2]}, north {e['bounds'][3]}")


if __name__ == "__main__":
    main()
