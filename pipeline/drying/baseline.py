# Written with Super Intelligence (SI) assistance.
"""Step 1 of drying: the intact-forest baseline for one track.

Rain, dew and calibration shift the whole scene up or down from pass to pass. Intact peat
swamp forest is a stable target at L-band (Jaenicke et al. 2011), so its median brightness
on each date measures that scene-wide shift. Later steps subtract it, which leaves the
change that is particular to a place.

Writes baseline_<track>.json (the per-date medians and offsets) and reference_<site>.tif.

    python pipeline/drying/baseline.py --stack pipeline/out/stacks/west_125.npz --out pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import numpy as np

from common import load_stack, lonlat, write_layer

REFERENCE = json.loads((Path(__file__).parent / "reference.json").read_text())


def reference_mask(stack):
    """Pixels of the reference forest: inside the box, data on every date, brighter half in season-mean HV."""
    lon, lat = lonlat(stack)
    west, south, east, north = REFERENCE["bbox"]
    box = stack["cov"] & (lon > west) & (lon < east) & (lat > south) & (lat < north)
    hv_mean = np.nanmean(stack["hv"], axis=0)
    return box & (hv_mean > np.nanmedian(hv_mean[box])), box


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stack", required=True, type=Path, help="the stack of the site that holds the reference forest")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stack)
    track = a.stack.stem.split("_")[1]
    ref, box = reference_mask(stack)

    result = {"track": track, "reference_site": REFERENCE["site"], "reference_bbox": REFERENCE["bbox"],
              "reference_km2": round(float(ref.sum()) * 0.0025, 1), "box_km2": round(float(box.sum()) * 0.0025, 1),
              "fire_excluded": False, "dates": stack["dates"]}
    for pol in ("hh", "hv"):
        med = np.array([float(np.nanmedian(layer[ref])) for layer in stack[pol]])
        result[pol] = {"median_db": [round(v, 3) for v in med],
                       # offset = how far each date sits from the season mean of the reference
                       "offset_db": [round(v, 3) for v in med - med.mean()],
                       "range_db": round(float(med.max() - med.min()), 3)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"baseline_{track}.json").write_text(json.dumps(result, indent=1) + "\n")
    write_layer(a.out / f"reference_{REFERENCE['site']}.tif", ref.astype("float32"), stack, layer="reference forest", track=track)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
