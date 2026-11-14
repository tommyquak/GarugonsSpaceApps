# Written with Super Intelligence (SI) assistance.
"""A second, independent peat map for one site: CIFOR's tropical peatland map. For local use only.

Gumbricht et al. 2017 (Global Change Biology, doi 10.1111/gcb.13689; data doi
10.17528/CIFOR/DATA.00058) mapped peat across the tropics from a hydrological model, yearly
satellite soil moisture and landforms, at about 231 m. It does not draw on the national peat
survey that PEATMAP and the official map in peat.py both use, so its agreement with PEATMAP is
an independent check of the boundary every number rests on (docs/LIMITS.md, "One peat map").
Its authors found 65% agreement with 275 soil profiles that contain peat.

Licence: the dataset page says CC BY 4.0, but the terms inside the file make it CIFOR's
property and require written permission for commercial use. Until that is settled, the raster
built here stays on your machine: it is never committed and never released. Only the numbers
computed from it are reported.

Downloads the archive once (41 MB, 332 MB unpacked) into data/cifor/ and writes
<layers>/peat_cifor_<site>.tif (1 on CIFOR peat, 0 off it, on the dry-down grid, nearest
neighbour). Against peat_peatmap_<site>.tif it writes to validation.json:

  peat_map_agreement_cifor_<site>    share of cells where CIFOR and PEATMAP say the same
  peat_map_agreement_cifor_chance_<site>  the same for two unrelated maps with these peat shares
  peat_cifor_in_peatmap_<site>     share of CIFOR peat that PEATMAP maps as peat too
  peatmap_in_cifor_<site>            share of PEATMAP peat that CIFOR maps as peat too
  peat_km2_cifor_<site>              CIFOR peat with radar data on both orbits
  fell_1db_km2_on_cifor_peat_<site>  land that fell 1 dB or more on both orbits, on CIFOR peat
  fire_share_on_cifor_peat_<site>    share of CIFOR peat inside a fire detection's footprint

The last three are the PEATMAP numbers of pipeline/drying/split.py with the other boundary.

    python pipeline/context/peat_cifor.py --site west --layers pipeline/out/layers
"""
import argparse
import json
import sys
from pathlib import Path

import certifi
import numpy as np
import rasterio
import requests
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/context/peat_cifor.py"
ARCHIVE = "https://data.cifor.org/api/access/datafile/3261"   # TROP-SUBTROP_PeatV21_2016_CIFOR.7z
ARCHIVE_NAME, TIF_NAME = "TROP-SUBTROP_PeatV21_2016_CIFOR.7z", "TROP-SUBTROP_PeatV21_2016_CIFOR.tif"
CITATION = "CIFOR tropical peatland map, Gumbricht et al. 2017, doi 10.17528/CIFOR/DATA.00058"
SITES = json.loads((Path(__file__).resolve().parents[1] / "radar" / "sites.json").read_text())
KM2 = 0.0025          # one 50 m cell
STRONG_DB = -1.0      # the fall that counts, as in pipeline/drying/split.py
MARGIN_DEG = 0.05
OUT_NODATA = 255


def fetch(keep):
    """The CIFOR GeoTIFF, downloaded and unpacked once into `keep`."""
    tif = keep / TIF_NAME
    if tif.exists():
        return tif
    keep.mkdir(parents=True, exist_ok=True)
    archive = keep / ARCHIVE_NAME
    if not archive.exists():
        with requests.get(ARCHIVE, stream=True, timeout=600, verify=certifi.where()) as r:
            r.raise_for_status()
            with open(archive, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    import py7zr     # only needed to unpack, once
    with py7zr.SevenZipFile(archive) as z:
        z.extract(path=keep, targets=[TIF_NAME])
    return tif


def on_grid(src, bbox, profile):
    """CIFOR peat for `bbox` (lon/lat) on the grid in `profile`: 1 peat, 0 not, NaN where CIFOR has no data."""
    west, south, east, north = bbox
    win = from_bounds(west - MARGIN_DEG, south - MARGIN_DEG, east + MARGIN_DEG, north + MARGIN_DEG, src.transform)
    win = win.round_offsets().round_lengths()
    out = np.full((profile["height"], profile["width"]), OUT_NODATA, "uint8")
    reproject(src.read(1, window=win), out, src_transform=src.window_transform(win), src_crs=src.crs, src_nodata=src.nodata,
              dst_transform=profile["transform"], dst_crs=profile["crs"], dst_nodata=OUT_NODATA, resampling=Resampling.nearest)
    peat = out.astype("float32")
    peat[out == OUT_NODATA] = np.nan
    return peat


def compare(cifor, peatmap, valid=None, strong=None, fire=None):
    """How CIFOR peat lines up with PEATMAP, and the PEATMAP-based headline numbers redone on CIFOR peat.
    `cifor` may hold NaN; `peatmap` is 1 or 0. `valid` is radar data on both orbits, `strong` a fall of
    1 dB or more on both, `fire` inside a detection's footprint. Missing inputs leave their numbers out."""
    has = np.isfinite(cifor)
    c, p = (cifor == 1) & has, peatmap == 1
    fc, fp = c[has].mean(), p[has].mean()
    out = {"agreement": float((c == p)[has].mean()),
           "chance": float(fc * fp + (1 - fc) * (1 - fp)),    # what two unrelated maps with these peat shares would give
           "cifor_in_peatmap": float((c & p).sum() / max(c.sum(), 1)),
           "peatmap_in_cifor": float((c & p & has).sum() / max((p & has).sum(), 1))}
    if valid is not None:
        out["km2"] = float((valid & c).sum() * KM2)
        if strong is not None:
            out["fell_1db_km2"] = float((strong & c).sum() * KM2)
            out["fell_1db_km2_peatmap"] = float((strong & p).sum() * KM2)
        if fire is not None:
            zone = valid & c
            out["fire_share"] = float((zone & fire).sum() / max(zone.sum(), 1))
    return out


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", required=True, choices=sorted(SITES))
    p.add_argument("--layers", required=True, type=Path)
    p.add_argument("--keep", default=Path("data/cifor"), type=Path, help="where the downloaded map is kept")
    a = p.parse_args(argv)

    drydowns = sorted(a.layers.glob(f"drydown_{a.site}_*.tif"))
    if not drydowns:
        raise SystemExit(f"no drydown_{a.site}_*.tif in {a.layers}: the grid comes from it")
    with rasterio.open(drydowns[0]) as src:
        profile = src.profile.copy()
    with rasterio.open(fetch(a.keep)) as src:
        cifor = on_grid(src, SITES[a.site]["bbox"], profile)
    with rasterio.open(a.layers / f"peat_cifor_{a.site}.tif", "w", **{**profile, "dtype": "float32", "nodata": np.nan}) as dst:
        dst.write(cifor, 1)
        dst.update_tags(layer="mapped peat, CIFOR (local use only)", source=CITATION)
    has = np.isfinite(cifor)
    line = f"{a.site}: CIFOR maps {(cifor == 1).sum() * KM2:.0f} km2 as peat ({(cifor == 1)[has].mean():.0%} of the grid it covers)"

    peat_file = a.layers / f"peat_peatmap_{a.site}.tif"
    if not peat_file.exists():
        print(line + f"; {peat_file.name} is not there yet, no comparison")
        return
    peatmap = read(peat_file)
    if peatmap.shape != cifor.shape:
        raise SystemExit(f"{peat_file.name} is not on the grid of {drydowns[0].name}")
    valid = strong = fire = None
    if len(drydowns) == 2:
        asc, desc = (read(f) for f in drydowns)
        valid = np.isfinite(asc) & np.isfinite(desc)
        strong = valid & (asc < STRONG_DB) & (desc < STRONG_DB)
    fire_file = a.layers / f"fire_days_{a.site}.tif"
    if valid is not None and fire_file.exists():
        fire = np.nan_to_num(read(fire_file)) > 0
    m = compare(cifor, peatmap, valid, strong, fire)

    put(f"peat_map_agreement_cifor_{a.site}", m["agreement"], "share of cells", a.site, ME,
        note="cells where the CIFOR map and PEATMAP say the same; CIFOR is an independent mapping")
    put(f"peat_map_agreement_cifor_chance_{a.site}", m["chance"], "share of cells", a.site, ME,
        note="the agreement two unrelated maps with the same peat shares would reach; compare with peat_map_agreement_cifor")
    put(f"peat_cifor_in_peatmap_{a.site}", m["cifor_in_peatmap"], "share of CIFOR peat", a.site, ME, note="CIFOR peat that PEATMAP maps as peat too")
    put(f"peatmap_in_cifor_{a.site}", m["peatmap_in_cifor"], "share of PEATMAP peat", a.site, ME, note="PEATMAP peat that CIFOR maps as peat too")
    line += f"; agrees with PEATMAP on {m['agreement']:.0%} of cells (unrelated maps: {m['chance']:.0%}), {m['peatmap_in_cifor']:.0%} of PEATMAP peat is CIFOR peat and {m['cifor_in_peatmap']:.0%} the other way"
    if "km2" in m:
        put(f"peat_km2_cifor_{a.site}", m["km2"], "km2", a.site, ME, note="CIFOR peat with radar data on both orbits")
    if "fell_1db_km2" in m:
        put(f"fell_1db_km2_on_cifor_peat_{a.site}", m["fell_1db_km2"], "km2", a.site, ME, note="fell by 1 dB or more in HH on both orbits, on CIFOR peat")
        line += f"; fell 1 dB or more on CIFOR peat {m['fell_1db_km2']:.0f} km2 against {m['fell_1db_km2_peatmap']:.0f} km2 on PEATMAP peat"
    if "fire_share" in m:
        put(f"fire_share_on_cifor_peat_{a.site}", m["fire_share"], "share of zone", a.site, ME, note="CIFOR peat inside the footprint of a 2026 fire detection")
        line += f"; fire on {m['fire_share']:.0%} of CIFOR peat"
    print(line)


if __name__ == "__main__":
    main()
