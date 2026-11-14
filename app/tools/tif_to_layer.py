# Written with Super Intelligence (SI) assistance.
"""Turn pipeline GeoTIFFs into map images for the app.

For each GeoTIFF (docs/DATA_CONTRACT.md section 2) this writes `<id>.png`, drawn in Web
Mercator with no-data transparent, and adds or replaces the entry with that id in
`layers.json` (section 5). The colours come from the file name:

    drydown_<site>_<track>.tif        fall in HH over the dry season, 1 to 3 dB
    hh_<site>_<track>_<YYYYMMDD>.tif  the same ramp for one radar pass, with its date
    dried_<site>.tif                  one colour where the value is 1
    recovery_<pol>_<site>.tif         rise across the first rain, 0.5 to 2 dB
    fire_days_<site>.tif              black where a fire was detected on one day or more
    anything else                     a neutral ramp between the 2nd and 98th percentile

    python app/tools/tif_to_layer.py pipeline/out/layers/drydown_west_125.tif
    python app/tools/tif_to_layer.py pipeline/out/layers/hh_west_125_*.tif
    python app/tools/tif_to_layer.py some.tif --style fall --range 0.5 2 --title "My layer"

Needs numpy, rasterio and Pillow. Peat boundary files (`peat_*`) are refused unless
--allow-peat is given: they stay out of git until their licence is confirmed.
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "public" / "layers"

# Same stops as pipeline/drying/one_look_map.py, so the app and the static map agree.
DRY = ["#f6e27a", "#f0a04b", "#d9502e", "#8f1d1d", "#4a0d12"]
WET = ["#c9ecf2", "#6cc3dc", "#2b8cc4", "#1d4f9c", "#162a63"]
NEUTRAL = ["#2a2f6b", "#3f6f9a", "#4fa39a", "#8fcf78", "#f2e55c"]

RADAR = "NISAR L2 GCOV, ASF DAAC"
ORBIT = {"125": "ascending, dawn", "010": "ascending, dawn", "061": "descending, dusk", "119": "descending, dusk"}

# style -> how values become colours.
#   sign  : -1 colours the fall (negative values), +1 the rise
#   range : value at the first and the last colour; anything short of the first is transparent
STYLES = {
    "fall": {"sign": -1, "range": [1.0, 3.0], "colors": DRY, "legend": "sequential", "unit": "dB"},
    "rise": {"sign": +1, "range": [0.5, 2.0], "colors": WET, "legend": "sequential", "unit": "dB"},
    "mask": {"colors": ["#d9502e"], "legend": "mask", "unit": None},
    "fire": {"colors": ["#000000"], "legend": "mask", "unit": "days"},
    "auto": {"sign": +1, "range": None, "colors": NEUTRAL, "legend": "sequential", "unit": None},
}


def track_label(track):
    return f"track {track}" + (f" ({ORBIT[track]})" if track in ORBIT else "")


def describe(stem):
    """Style, title, date and source for a file name of the data contract."""
    m = re.fullmatch(r"hh_([a-z]+)_(\d{3})_(\d{4})(\d{2})(\d{2})", stem)
    if m:
        return {"style": "fall", "title": f"Fall in HH since the start of the season, {track_label(m[2])}",
                "date": f"{m[3]}-{m[4]}-{m[5]}", "source": RADAR}
    m = re.fullmatch(r"drydown_([a-z]+)_(\d{3})", stem)
    if m:
        return {"style": "fall", "title": f"Fall in HH over the dry season, {track_label(m[2])}", "source": RADAR}
    if re.fullmatch(r"dried_[a-z]+", stem):
        return {"style": "mask", "title": "Dried beyond the noise floor on both orbits", "source": RADAR}
    m = re.fullmatch(r"recovery_(hh|hv)_[a-z]+", stem)
    if m:
        return {"style": "rise", "title": f"Rise in {m[1].upper()} across the first rain", "source": RADAR}
    if re.fullmatch(r"fire_days_[a-z]+", stem):
        return {"style": "fire", "title": "Fire detected in 2026", "source": "NASA FIRMS (VIIRS and MODIS)"}
    return {"style": "auto", "title": stem.replace("_", " "), "source": None}


def rgb(hex_colour):
    return [int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)]


def colourise(values, style, value_range):
    """Palette image of a 2-D float array: index 0 is transparent, 1 to 255 run along the ramp.

    A palette keeps the files small enough to commit: about a quarter of the size of full colour.
    """
    stops = np.array([rgb(c) for c in style["colors"]], dtype=float)
    ok = np.isfinite(values)
    if len(stops) == 1:  # one colour where the value is above zero
        index = (ok & (np.where(ok, values, 0) > 0)).astype(np.uint8)
        ramp = stops[:1]
    else:
        lo, hi = value_range
        t = (np.where(ok, values, np.nan) * style["sign"] - lo) / (hi - lo)
        show = ok & (t >= 0)
        index = np.where(show, 1 + np.round(np.clip(np.where(show, t, 0), 0, 1) * 254), 0).astype(np.uint8)
        x = np.linspace(0, 1, len(stops))
        ramp = np.stack([np.interp(np.linspace(0, 1, 255), x, stops[:, band]) for band in range(3)], axis=1)
    image = Image.fromarray(index, "P")
    image.putpalette([0, 0, 0] + [int(v) for v in np.round(ramp).astype(int).ravel()])
    image.info["transparency"] = 0
    return image, index


def to_web_mercator(path, max_size):
    """Band 1 of a GeoTIFF on a north-up Web Mercator grid, and its bounds in degrees."""
    with rasterio.open(path) as src:
        data = src.read(1).astype("float32")
        if src.nodata is not None and not np.isnan(src.nodata):
            data[data == src.nodata] = np.nan
        transform, width, height = calculate_default_transform(src.crs, "EPSG:3857", src.width, src.height, *src.bounds)
        shrink = max(width, height) / max_size
        if shrink > 1:
            width, height = int(np.ceil(width / shrink)), int(np.ceil(height / shrink))
            transform = transform * transform.scale(shrink, shrink)
        out = np.full((height, width), np.nan, dtype="float32")
        reproject(data, out, src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
                  dst_transform=transform, dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.nearest)
    left, top = transform * (0, 0)
    right, bottom = transform * (width, height)
    west, south, east, north = transform_bounds("EPSG:3857", "EPSG:4326", left, bottom, right, top)
    return out, [round(x, 6) for x in (west, south, east, north)]


def convert(path, out_dir, a):
    stem = path.stem
    if stem.startswith("peat_") and not a.allow_peat:
        sys.exit(f"{path.name}: peat boundary files are not committed until the licence is confirmed "
                 "(docs/DATA_CONTRACT.md section 2). Pass --allow-peat for local use only.")
    info = describe(stem)
    style_name = a.style or info["style"]
    style = STYLES[style_name]
    date = a.date or info.get("date")
    values, bounds = to_web_mercator(path, a.max_size or (1024 if date else 2048))
    value_range = a.range or style.get("range")
    if len(style["colors"]) > 1 and value_range is None:
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            sys.exit(f"{path.name}: no data in band 1")
        value_range = [float(x) for x in np.percentile(finite * style["sign"], [2, 98])]
    if value_range is not None and not value_range[0] < value_range[1]:
        sys.exit(f"{path.name}: the range must go from a smaller to a larger number, got {value_range}")

    image, index = colourise(values, style, value_range)
    layer_id = a.id or stem
    out_dir.mkdir(parents=True, exist_ok=True)
    image.save(out_dir / f"{layer_id}.png", optimize=True, transparency=0)

    entry = {
        "id": layer_id,
        "title": a.title or info["title"],
        "url": f"layers/{layer_id}.png",
        "bounds": bounds,
        "date": date,
        "unit": a.unit or style["unit"],
        "legend": style["legend"],
        "source": a.source or info["source"],
        # Extra keys for drawing the legend: the values at the first and last colour, and the colours.
        "range": None if len(style["colors"]) == 1 else [round(float(x), 3) for x in value_range],
        "colors": style["colors"],
    }
    shown = int((index > 0).sum())
    print(f"{layer_id}.png  {index.shape[1]}x{index.shape[0]}  {shown / max(1, int(np.isfinite(values).sum())):.0%} of data coloured")
    return entry


def update_index(index_path, entries):
    """Add the entries to layers.json, replacing any with the same id and keeping the order."""
    layers = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    position = {layer["id"]: i for i, layer in enumerate(layers)}
    for entry in entries:
        if entry["id"] in position:
            layers[position[entry["id"]]] = entry
        else:
            position[entry["id"]] = len(layers)
            layers.append(entry)
    index_path.write_text(json.dumps(layers, indent=2) + "\n", encoding="utf-8")
    return len(layers)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tifs", nargs="+", help="GeoTIFF files; wildcards are expanded")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="folder for the images and layers.json (default: app/public/layers)")
    p.add_argument("--style", choices=sorted(STYLES), help="override the style picked from the file name")
    p.add_argument("--range", nargs=2, type=float, metavar=("FIRST", "LAST"), help="values at the first and the last colour")
    p.add_argument("--max-size", type=int, help="longest side of the image in pixels (default: 2048, or 1024 for a dated layer, "
                   "because the slider needs one image per pass)")
    p.add_argument("--allow-peat", action="store_true", help="convert peat_* files, for local use only")
    for key in ("id", "title", "date", "unit", "source"):
        p.add_argument(f"--{key}", help=f"override '{key}' in the layers.json entry (one input file only)")
    a = p.parse_args()

    paths = [Path(f) for pattern in a.tifs for f in (sorted(glob.glob(pattern)) or [pattern])]
    missing = [str(f) for f in paths if not f.is_file()]
    if missing:
        sys.exit("not found: " + ", ".join(missing))
    if len(paths) > 1 and (a.id or a.title or a.date):
        sys.exit("--id, --title and --date apply to one input file at a time")
    if a.date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.date):
        sys.exit("--date must be YYYY-MM-DD")

    entries = [convert(f, a.out, a) for f in paths]
    total = update_index(a.out / "layers.json", entries)
    print(f"layers.json: {len(entries)} written, {total} in total, in {a.out}")


if __name__ == "__main__":
    main()
