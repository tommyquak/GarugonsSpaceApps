# Written with Super Intelligence (SI) assistance.
"""How much the recovery numbers depend on choices we made (track 2b).

recovery.py makes three choices: the last dry day (from the rainfall record, 25 Oct for now),
two passes for "late season", and the first pass after the rain. This reruns the recovery
with each choice moved by one step and reports how far the share of the fall regained moves,
in HH and HV, on the blocks that fell by 1 dB or more on both orbits:

  as run          the choices recovery.py uses
  late one pass   "late season" is the last dry pass alone, not the last two
  late earlier    "late season" is the two passes before the last dry one, in case it already caught rain
  second wet      the second pass after the rain, where there is one

and one placebo, which is not a variant: pretend the rain came one pass sooner, so the "pass
after the rain" is really the last dry pass. If the rebound is real, the placebo shows none.

Writes sensitivity_recovery_<site>_<track>.json next to the layers, the largest move of each
share and the placebo share to validation.json. A large move means the recovery number is a
choice, not a finding.

    python pipeline/recovery/sensitivity.py --site west --track 125 --other-track 061 --dry-until 20261025 \\
        --stacks pipeline/out/stacks --layers pipeline/out/layers
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_stack  # noqa: E402
from recovery import read, recover, strong_blocks, summarise  # noqa: E402
from vjson import get, put  # noqa: E402

ME = "pipeline/recovery/sensitivity.py"
PLACEBO = "placebo"


def variants(stack, base, dry_until):
    """The settings to try, as (name, dry_until, late_n, late_skip, wet_pass). The first is the one recovery.py
    uses, the last the placebo."""
    dry = [d for d in stack["dates"] if d <= dry_until]
    out = [("as run", dry_until, 2, 0, 0), ("late one pass", dry_until, 1, 0, 0)]
    if len(dry) >= 5:
        out.append(("late earlier", dry_until, 2, 1, 0))
    out.append(("second wet", dry_until, 2, 0, 1))
    if len(dry) >= 5:
        out.append((PLACEBO, dry[-2], 2, 0, 0))
    return out


def run(stack, base, fall_other, floor, dry_until, min_blocks=100):
    """Each variant's summary for HH and HV. Variants that cannot be run (no such pass) are left out."""
    rows = []
    for name, until, late_n, late_skip, wet_pass in variants(stack, base, dry_until):
        res = recover(stack, base, until, late_n=late_n, late_skip=late_skip, wet_pass=wet_pass)
        if res is None:
            continue
        out, _, after = res
        _, strong = strong_blocks(out, fall_other, stack["cov"])
        if strong.sum() < min_blocks:
            continue
        row = {"variant": name, "dry_until": until, "late_passes": late_n, "late_skip": late_skip, "after_pass": stack["dates"][after], "blocks": int(strong.sum())}
        for pol in ("hh", "hv"):
            row[pol] = summarise(out[pol], strong, floor)
        rows.append(row)
    return rows


def largest_move(rows, pol, key="regained"):
    """The largest distance of any variant from the as-run value. The placebo is not a variant."""
    ref = rows[0][pol][key]
    return max(abs(r[pol][key] - ref) for r in rows if r["variant"] != PLACEBO)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True)
    p.add_argument("--track", required=True)
    p.add_argument("--other-track", required=True)
    p.add_argument("--dry-until", required=True)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path)
    a = p.parse_args()
    stack = load_stack(a.stacks / f"{a.site}_{a.track}.npz")
    base = json.loads((a.layers / f"baseline_{a.track}.json").read_text())
    fall_other = read(a.layers / f"drydown_{a.site}_{a.other_track}.tif")
    floor = abs(get(f"noise_floor_hh_{a.track}")["value"])
    rows = run(stack, base, fall_other, floor, a.dry_until)
    tag = f"{a.site}_{a.track}"
    if not rows or rows[0]["variant"] != "as run":
        print(f"{tag}: no pass after {a.dry_until} yet, skipped")
        return
    (a.layers / f"sensitivity_recovery_{tag}.json").write_text(json.dumps(rows, indent=1) + "\n")
    tried = ", ".join(r["variant"] for r in rows[1:] if r["variant"] != PLACEBO)
    placebo = next((r for r in rows if r["variant"] == PLACEBO), None)
    for pol in ("hh", "hv"):
        move = largest_move(rows, pol)
        put(f"recovery_{pol}_share_regained_sensitivity_{tag}", move, "share of the fall", a.site, ME,
            note=f"largest move from the as-run value over: {tried}")
        if placebo:
            put(f"recovery_{pol}_share_regained_placebo_{tag}", placebo[pol]["regained"], "share of the fall", a.site, ME,
                note=f"rain pretended one pass sooner, so the 'rebound' is {placebo['after_pass']} against the two dry passes before it; "
                     "near zero or negative means the rebound comes with the rain")
    print(f"{tag}: share of the fall regained, as run and under each variant")
    for r in rows:
        print(f"   {r['variant']:<16} HH {r['hh']['regained']:.0%}  HV {r['hv']['regained']:.0%}  ({r['blocks']} blocks, after pass {r['after_pass']})")


if __name__ == "__main__":
    main()
