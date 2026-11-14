# Written with Super Intelligence (SI) assistance.
"""Set the radar beside the modelled water table at the two gauge sites.

For each site and each orbit: the HH and HV brightness of the 1 km around the gauge on every
pass (HH with the scene-wide shift removed, HV as measured), next to the water table that
model.py gives for the same day from 2026 rainfall.

What this can and cannot show. Both curves answer the same rain, so some agreement is
guaranteed, and ten or eleven passes are few. Agreement means the radar behaves as a
physically based estimate of the water table would lead one to expect. It is not a
measurement of the water table, and the 2026 water table is modelled, not observed. The
correlation of pass-to-pass changes is reported next to the plain correlation because two
curves that both fall through a season correlate whatever they measure.

Writes radar_vs_water_table.json and entries in validation.json.

    python pipeline/hydro/compare.py --hydro pipeline/out/hydro --stacks pipeline/out/stacks --layers pipeline/out/layers
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
from common import load_stack  # noqa: E402
from drydown import normalised  # noqa: E402
from vjson import put  # noqa: E402

ME = "pipeline/hydro/compare.py"
CONFIG = json.loads((Path(__file__).parent / "sites.json").read_text())
HALF_WINDOW = 10      # 10 pixels of 50 m each side: about 1 km across


def at_site(layers, stack, lon, lat):
    """Median over the window around a point, for every pass."""
    x, y = Transformer.from_crs(4326, stack["epsg"], always_xy=True).transform(lon, lat)
    col, row = (int(v) for v in ~stack["T"] * (x, y))
    rows, cols = stack["cov"].shape
    if not (HALF_WINDOW <= row < rows - HALF_WINDOW and HALF_WINDOW <= col < cols - HALF_WINDOW):
        raise SystemExit("the site is outside the radar window")
    box = (slice(row - HALF_WINDOW, row + HALF_WINDOW + 1), slice(col - HALF_WINDOW, col + HALF_WINDOW + 1))
    return [float(np.nanmedian(layer[box])) for layer in layers]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hydro", required=True, type=Path)
    p.add_argument("--stacks", required=True, type=Path)
    p.add_argument("--layers", required=True, type=Path, help="folder with baseline_<track>.json")
    p.add_argument("--tracks", nargs="+", default=["125", "061"])
    p.add_argument("--year", default="2026")
    a = p.parse_args()
    modelled = json.loads((a.hydro / "water_table_modelled.json").read_text())
    out = {"label": "the water table is modelled from rainfall, not measured", "window_m": (2 * HALF_WINDOW + 1) * 50, "sites": {}}
    for name, site in CONFIG["sites"].items():
        levels = modelled[name][a.year]
        out["sites"][name] = {"title": site["title"], "lon": site["lon"], "lat": site["lat"], "tracks": {}}
        for track in a.tracks:
            stack = load_stack(a.stacks / f"gauges_{track}.npz")
            base = json.loads((a.layers / f"baseline_{track}.json").read_text())
            days = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in stack["dates"]]
            hh = at_site(normalised(stack, base, "hh"), stack, site["lon"], site["lat"])
            hv = at_site(stack["hv"], stack, site["lon"], site["lat"])
            wt = [levels.get(d) for d in days]
            k = [i for i, v in enumerate(wt) if v is not None]
            w, h = np.array([wt[i] for i in k]), np.array([hh[i] for i in k])
            r = float(np.corrcoef(w, h)[0, 1])
            r_steps = float(np.corrcoef(np.diff(w), np.diff(h))[0, 1])
            slope = float(np.polyfit(w, h, 1)[0])
            out["sites"][name]["tracks"][track] = {"dates": days, "hh_db": [round(v, 2) for v in hh], "hv_db": [round(v, 2) for v in hv],
                                                  "modelled_water_table_m": wt, "r": round(r, 2), "r_of_changes": round(r_steps, 2),
                                                  "db_per_metre": round(slope, 2), "passes": len(k)}
            tag = f"{name}_{track}"
            put(f"hydro_radar_r_{tag}", r, "Pearson r", "gauges", ME, note=f"HH against the MODELLED water table over {len(k)} passes; two seasonal curves, so read r_of_changes too")
            put(f"hydro_radar_r_of_changes_{tag}", r_steps, "Pearson r", "gauges", ME, note="pass-to-pass change in HH against pass-to-pass change in the modelled water table")
            put(f"hydro_radar_db_per_metre_{tag}", slope, "dB per m", "gauges", ME, note="slope of HH on the modelled water table; not a calibration")
            print(f"{name} ({site['title'].lower()}) track {track}: HH range {max(hh) - min(hh):.2f} dB, modelled water table {min(w):.2f} to {max(w):.2f} m; "
                  f"r {r:.2f}, r of changes {r_steps:.2f}, {slope:.2f} dB per m over {len(k)} passes")
    (a.hydro / "radar_vs_water_table.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
