# Written with Super Intelligence (SI) assistance.
"""One layer per radar pass, for the season slider.

For every pass of a stack: HH on that pass minus HH at the start of the season (the mean of
the start passes, chosen from --start-from as in drydown.py), with the scene-wide shift removed (baseline.py) and averaged over
250 m blocks. Negative means the place is darker than it was at the start. Passes after the
rain are included, so the slider also shows the land brightening again.

Writes hh_<site>_<track>_<YYYYMMDD>.tif for every date (docs/DATA_CONTRACT.md section 2).

    python pipeline/drying/per_pass.py --stack pipeline/out/stacks/west_125.npz \\
        --baseline pipeline/out/layers/baseline_125.json --out pipeline/out/layers
"""
import argparse
import json
from pathlib import Path

import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import block_mean, load_stack, write_layer  # noqa: E402
from drydown import normalised  # noqa: E402
from season import start_passes  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stack", required=True, type=Path)
    p.add_argument("--baseline", required=True, type=Path)
    p.add_argument("--start-from", help="YYYYMMDD, earliest day for a start pass; default: the first two passes")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stack)
    site, track = a.stack.stem.split("_")
    layers = normalised(stack, json.loads(a.baseline.read_text()), "hh")
    smooth = [block_mean(layer) for layer in layers]
    first = start_passes(stack["dates"], a.start_from)
    start = np.mean([smooth[i] for i in first], axis=0)
    a.out.mkdir(parents=True, exist_ok=True)
    line = []
    for date, layer in zip(stack["dates"], smooth):
        change = (layer - start).astype("float32")
        change[~stack["cov"]] = np.nan
        write_layer(a.out / f"hh_{site}_{track}_{date}.tif", change, stack, layer="HH change since the start of the season",
                    units="dB", track=track, date=date, start_passes=",".join(stack["dates"][i] for i in first))
        line.append(f"{date[4:]} {np.nanmedian(change):+.2f}")
    print(f"{site} {track}: median change by pass:", "  ".join(line))


if __name__ == "__main__":
    main()
