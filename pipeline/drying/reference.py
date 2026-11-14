# Written with Super Intelligence (SI) assistance.
"""Step 0 of drying: draw the intact reference forest once, for both orbits.

The reference must be the same ground for every track, or each track is measured against
a different yardstick. It must also be deep forest: our own check shows that forest within
a few kilometres of an edge, river or clearing darkens over the dry season, so edges are
signal, not a yardstick. A pixel is reference forest when:

  - it has data on every date of both tracks,
  - its season-mean HV, averaged over a 250 m block, is above the darkest fifth of the
    reference box on both tracks (rivers, clearings and burn scars are dark in HV),
  - it is at least 4 km inside the forest that this test finds across the whole site,
  - and it lies inside the box of reference.json.

Writes reference_<site>.tif (1 forest, 0 not), forest_depth_<site>.tif (kilometres into
the forest, 0 outside it) and reference_<site>.json.

    python pipeline/drying/reference.py --stacks pipeline/out/stacks/west_125.npz pipeline/out/stacks/west_061.npz \\
        --out pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from common import block_mean, load_stack, lonlat, write_layer

REFERENCE = json.loads((Path(__file__).parent / "reference.json").read_text())
DROP_DARKEST = 20    # per cent of the box, by block-mean HV, that is not counted as forest
DEPTH_KM = 4.0       # how far inside the forest the reference starts


def forest_depth(stacks, drop=DROP_DARKEST):
    """Kilometres from each forest pixel to the nearest non-forest pixel, and the reference box."""
    lon, lat = lonlat(stacks[0])
    west, south, east, north = REFERENCE["bbox"]
    box = (lon > west) & (lon < east) & (lat > south) & (lat < north)
    forest = np.ones(box.shape, bool)
    for s in stacks:
        forest &= s["cov"]
    for s in stacks:
        with np.errstate(all="ignore"):
            hv = block_mean(np.nanmean(s["hv"], axis=0))
        forest &= hv > np.nanpercentile(hv[box & s["cov"]], drop)
    return (distance_transform_edt(forest) * 0.05).astype("float32"), box


def reference_mask(stacks, drop=DROP_DARKEST, depth_km=DEPTH_KM):
    depth, box = forest_depth(stacks, drop)
    return box & (depth >= depth_km), box


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stacks", nargs="+", required=True, type=Path, help="every track's stack of the reference site")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    stacks = [load_stack(f) for f in a.stacks]
    depth, box = forest_depth(stacks)
    ref = box & (depth >= DEPTH_KM)
    info = {"site": REFERENCE["site"], "bbox": REFERENCE["bbox"], "tracks": [f.stem.split("_")[1] for f in a.stacks],
            "box_km2": round(float(box.sum()) * 0.0025, 1), "reference_km2": round(float(ref.sum()) * 0.0025, 1),
            "forest_km2_whole_site": round(float((depth > 0).sum()) * 0.0025, 1),
            "drop_darkest_percent": DROP_DARKEST, "depth_km": DEPTH_KM, "fire_excluded": False}
    a.out.mkdir(parents=True, exist_ok=True)
    write_layer(a.out / f"reference_{REFERENCE['site']}.tif", ref.astype("float32"), stacks[0], layer="reference forest")
    write_layer(a.out / f"forest_depth_{REFERENCE['site']}.tif", depth, stacks[0], layer="depth into forest", units="km")
    (a.out / f"reference_{REFERENCE['site']}.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
