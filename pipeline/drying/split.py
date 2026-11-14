# Written with Super Intelligence (SI) assistance.
"""Split the drying results by peat and by fire, once track 3's layers exist.

The radar shows where land dried. The peat boundary shows where that matters, and the fire
layer separates land that burned from land that only dried. This step reads:

  peat_peatmap_<site>.tif    1 on mapped peat, 0 off it        (track 3, PEATMAP, CC BY 4.0)
  fire_days_<site>.tif       days with a 2026 fire detection within 200 m   (track 3)

and writes, for every site, the areas and shares to validation.json: mapped peat, land that
fell by 1 dB or more on both orbits on peat and off it, how much of that is near fire, and
the two-orbit agreement on peat with no fire nearby. Peat fires are not the only fires, so
the same numbers are given off peat.

    python pipeline/drying/split.py --layers pipeline/out/layers --sites west east --tracks 125 061
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/drying/split.py"
KM2 = 0.0025
STRONG_DB = -1.0


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--sites", nargs="+", required=True)
    p.add_argument("--tracks", nargs=2, required=True)
    p.add_argument("--peat", default="peat_peatmap", help="name stem of the peat layer; peat_official is the local-only alternative")
    a = p.parse_args()
    for site in a.sites:
        peat_file, fire_file = a.layers / f"{a.peat}_{site}.tif", a.layers / f"fire_days_{site}.tif"
        if not peat_file.exists():
            print(f"{site}: {peat_file.name} is not there yet, skipped")
            continue
        asc, desc = (read(a.layers / f"drydown_{site}_{t}.tif") for t in a.tracks)
        valid = np.isfinite(asc) & np.isfinite(desc)
        peat = read(peat_file) == 1
        if peat.shape != asc.shape:
            raise SystemExit(f"{peat_file.name} is not on the grid of the drydown layers")
        strong = valid & (asc < STRONG_DB) & (desc < STRONG_DB)
        fire = (np.nan_to_num(read(fire_file)) > 0) if fire_file.exists() else None
        put(f"peat_km2_{site}", float((valid & peat).sum() * KM2), "km2", site, ME, note="mapped peat with radar data on both orbits")
        for zone_name, zone in (("on_peat", valid & peat), ("off_peat", valid & ~peat)):
            s = strong & zone
            put(f"fell_1db_km2_{zone_name}_{site}", float(s.sum() * KM2), "km2", site, ME, note="fell by 1 dB or more in HH on both orbits")
            put(f"fell_1db_share_{zone_name}_{site}", float(s.sum() / max(zone.sum(), 1)), "share of zone", site, ME)
            line = f"{site} {zone_name:8s}: zone {zone.sum() * KM2:6.0f} km2, fell 1 dB or more {s.sum() * KM2:6.0f} km2 ({s.sum() / max(zone.sum(), 1):.0%})"
            if fire is not None:
                put(f"fire_km2_{zone_name}_{site}", float((zone & fire).sum() * KM2), "km2", site, ME, note="within 200 m of a 2026 fire detection")
                put(f"fire_share_{zone_name}_{site}", float((zone & fire).sum() / max(zone.sum(), 1)), "share of zone", site, ME)
                put(f"fell_1db_no_fire_km2_{zone_name}_{site}", float((s & ~fire).sum() * KM2), "km2", site, ME, note="dried, with no fire detection within 200 m")
                put(f"fell_1db_near_fire_share_{zone_name}_{site}", float((s & fire).sum() / max(s.sum(), 1)), "share of the dried land", site, ME)
                line += f", of that near fire {(s & fire).sum() / max(s.sum(), 1):.0%}; fire in zone {(zone & fire).sum() * KM2:.0f} km2 ({(zone & fire).sum() / max(zone.sum(), 1):.0%})"
            print(line)
        if fire is not None:   # the cleanest test of the method: peat, no fire nearby, two independent orbits
            k = valid & peat & ~fire
            k[np.arange(k.shape[0]) % 5 != 2] = False
            k[:, np.arange(k.shape[1]) % 5 != 2] = False
            r = float(np.corrcoef(asc[k], desc[k])[0, 1])
            put(f"two_orbit_r_peat_no_fire_{site}", r, "Pearson r", site, ME, note=f"{int(k.sum())} blocks of 250 m on mapped peat with no fire nearby")
            print(f"{site}: two-orbit agreement on peat with no fire nearby r = {r:.2f} over {int(k.sum())} blocks")


if __name__ == "__main__":
    main()
