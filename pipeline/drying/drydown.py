# Written with Super Intelligence (SI) assistance.
"""Step 2 of drying: the dry-down score for one site and track.

For every pixel: HH brightness late in the dry season minus HH brightness at its start,
after removing the scene-wide shift measured on intact forest (baseline.py) and averaging
over 250 m blocks to steady the speckle. Negative means the place got darker than intact
forest did, which is what drying ground does at L-band (HH carries the ground signal).

"Start" is the mean of the first two passes. "Late" is the mean of the last two passes on
or before --dry-until, the last day before the rain came back (from the rainfall record).

Writes drydown_<site>_<track>.tif, in decibels, on the stack's grid.

    python pipeline/drying/drydown.py --stack pipeline/out/stacks/east_125.npz \\
        --baseline pipeline/out/layers/baseline_125.json --dry-until 20261025 --out pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import numpy as np

from common import block_mean, load_stack, write_layer


def normalised(stack, baseline, pol="hh"):
    """The stack with each date's scene-wide offset removed."""
    if baseline["dates"] != stack["dates"]:
        raise SystemExit("the baseline and the stack do not list the same dates: build them from the same track")
    offsets = np.array(baseline[pol]["offset_db"], dtype="float32")
    return stack[pol] - offsets[:, None, None]


def drydown(stack, baseline, dry_until, pol="hh"):
    use = [i for i, d in enumerate(stack["dates"]) if d <= dry_until]
    if len(use) < 4:
        raise SystemExit("need at least four passes on or before --dry-until")
    layers = normalised(stack, baseline, pol)
    first = np.mean([block_mean(layers[i]) for i in use[:2]], axis=0)
    late = np.mean([block_mean(layers[i]) for i in use[-2:]], axis=0)
    return (late - first).astype("float32"), [stack["dates"][i] for i in use[:2]], [stack["dates"][i] for i in use[-2:]]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stack", required=True, type=Path)
    p.add_argument("--baseline", required=True, type=Path, help="baseline_<track>.json for the same track")
    p.add_argument("--dry-until", required=True, help="YYYYMMDD, last day before the rain returned")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stack)
    site, track = a.stack.stem.split("_")
    change, first, late = drydown(stack, json.loads(a.baseline.read_text()), a.dry_until)
    change[~stack["cov"]] = np.nan
    a.out.mkdir(parents=True, exist_ok=True)
    write_layer(a.out / f"drydown_{site}_{track}.tif", change, stack, layer="HH dry-down", units="dB", track=track,
                first_passes=",".join(first), late_passes=",".join(late), dry_until=a.dry_until)
    q = np.nanpercentile(change, [5, 25, 50, 75, 95])
    print(f"{site} {track}: first {first}, late {late}; change dB p5 {q[0]:.2f} p25 {q[1]:.2f} median {q[2]:.2f} p75 {q[3]:.2f} p95 {q[4]:.2f}")


if __name__ == "__main__":
    main()
