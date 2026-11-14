# Written with Super Intelligence (SI) assistance.
"""How much do the drying results depend on choices we made?

  passes   which passes count as "start" and "late"
  block    the block size the score is averaged over
  pol      HH (our choice) against HV
  class    do the two orbits pick the same strongly dried land?

For each variant: the agreement between the two orbits, the noise floor, and the share of
the site that falls by 1 dB or more on both orbits. Writes sensitivity.json next to the layers.

    python pipeline/drying/sensitivity.py --stacks pipeline/out/stacks --layers pipeline/out/layers --dry-until 20261025
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import block_mean, load_reference, load_stack  # noqa: E402
from drydown import normalised  # noqa: E402


def score(stack, base, dry_until, pol="hh", first=(0, 1), late=(-2, -1), size=5, slope=False):
    use = [i for i, d in enumerate(stack["dates"]) if d <= dry_until]
    layers = normalised(stack, base, pol)
    sm = {i: block_mean(layers[i], size) for i in (use if slope else {use[j] for j in first + late})}
    if slope:   # straight-line fit through every dry-season pass, scaled to the length of the season
        days = np.array([(np.datetime64(f"{d[:4]}-{d[4:6]}-{d[6:]}") - np.datetime64("2026-01-01")).astype(int) for d in (stack["dates"][i] for i in use)], dtype="float32")
        t = days - days.mean()
        cube = np.array([sm[i] for i in use])
        return ((cube * t[:, None, None]).sum(0) / (t ** 2).sum() * (days.max() - days.min())).astype("float32")
    return (np.mean([sm[use[j]] for j in late], axis=0) - np.mean([sm[use[j]] for j in first], axis=0)).astype("float32")


def summarise(sa, sd, ref, size):
    step = max(size, 5)
    pick = np.zeros(ref.shape, bool); pick[step // 2::step, step // 2::step] = True
    solid = block_mean(ref.astype("float32"), size) > 0.95
    k = pick & np.isfinite(sa) & np.isfinite(sd)
    fa, fd = np.percentile(sa[k & solid], 5), np.percentile(sd[k & solid], 5)
    strong_a, strong_d = sa < -1.0, sd < -1.0
    both, either = (strong_a & strong_d & k).sum(), ((strong_a | strong_d) & k).sum()
    return {"two_orbit_r": round(float(np.corrcoef(sa[k], sd[k])[0, 1]), 3), "floor_asc_db": round(float(fa), 2), "floor_desc_db": round(float(fd), 2),
            "share_1db_both": round(float(both / k.sum()), 3), "strong_class_overlap": round(float(both / max(either, 1)), 3),
            "reference_flagged": round(float(((sa < fa) & (sd < fd) & k & solid).sum() / max((k & solid).sum(), 1)), 3)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--site", default="west")
    p.add_argument("--tracks", nargs=2, default=["125", "061"])
    p.add_argument("--dry-until", required=True)
    a = p.parse_args()
    S = [load_stack(a.stacks / f"{a.site}_{t}.npz") for t in a.tracks]
    B = [json.loads((a.layers / f"baseline_{t}.json").read_text()) for t in a.tracks]
    ref = load_reference(a.layers)
    variants = {
        "default: HH, first two against last two, 250 m": {},
        "passes: first one against last one": {"first": (0,), "late": (-1,)},
        "passes: first three against last three": {"first": (0, 1, 2), "late": (-3, -2, -1)},
        "passes: second and third against last two": {"first": (1, 2)},
        "passes: straight-line fit through every pass": {"slope": True},
        "block: 150 m": {"size": 3},
        "block: 550 m": {"size": 11},
        "block: none (50 m pixels)": {"size": 1},
        "pol: HV instead of HH": {"pol": "hv"},
    }
    out, default = {}, None
    for name, kw in variants.items():
        sa, sd = (score(s, b, a.dry_until, **kw) for s, b in zip(S, B))
        out[name] = summarise(sa, sd, ref, kw.get("size", 5))
        if default is None:
            default = sa
        else:
            k = np.isfinite(sa) & np.isfinite(default)
            out[name]["r_with_default_asc"] = round(float(np.corrcoef(sa[k][::25], default[k][::25])[0, 1]), 3)
        print(f"{name:48s}", json.dumps(out[name]))
    (a.layers / "sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
