# Written with Super Intelligence (SI) assistance.
"""Step 1 of drying: the intact-forest baseline for one track.

Rain, dew and calibration shift the whole scene up or down from pass to pass. Intact peat
swamp forest is a stable target at L-band (Jaenicke et al. 2011), so its median brightness
on each date measures that scene-wide shift. Later steps subtract it, which leaves the
change that is particular to a place.

The forest itself is drawn once for all tracks by reference.py. Writes baseline_<track>.json
(the per-date medians and offsets).

    python pipeline/drying/baseline.py --stack pipeline/out/stacks/west_125.npz \\
        --reference pipeline/out/layers/reference_west.tif --out pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

from common import load_stack


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stack", required=True, type=Path, help="the stack of the site that holds the reference forest")
    p.add_argument("--reference", required=True, type=Path, help="reference_<site>.tif from reference.py")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stack)
    site, track = a.stack.stem.split("_")
    with rasterio.open(a.reference) as src:
        ref = src.read(1) == 1
    if ref.shape != stack["cov"].shape:
        raise SystemExit("the reference layer and the stack are on different grids")

    result = {"track": track, "reference_site": site, "reference_km2": round(float(ref.sum()) * 0.0025, 1),
              "dates": stack["dates"]}
    for pol in ("hh", "hv"):
        med = np.array([float(np.nanmedian(layer[ref])) for layer in stack[pol]])
        result[pol] = {"median_db": [round(v, 3) for v in med],
                       # offset = how far each date sits from the season mean of the reference
                       "offset_db": [round(v, 3) for v in med - med.mean()],
                       "range_db": round(float(med.max() - med.min()), 3)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"baseline_{track}.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
