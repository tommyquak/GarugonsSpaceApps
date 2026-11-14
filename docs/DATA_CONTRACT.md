# Data contract

The file formats the tracks hand to each other. If you need to change one, change this file in the same PR and tag the owners it affects on the board.

Nothing in this file is committed to git except the small app files in section 4. Stacks and layers are attached to a GitHub release.

## 1. Radar stacks (track 1 writes; tracks 2, 3 and 5 read)

One file per site and orbit: `<site>_<track>.npz`, for example `west_125.npz`.

| Key | Type | Meaning |
|---|---|---|
| `hh`, `hv` | float32, shape (dates, rows, cols) | Gamma-nought backscatter in decibels, averaged to 50 m. NaN where there is no data. |
| `cov` | bool, shape (rows, cols) | True where every date has data in both polarisations. |
| `T` | 6 floats | Affine transform of the grid (a, b, c, d, e, f), pixel corner convention. |
| `crs` | int | EPSG code of the grid. |
| `dates` | list of `YYYYMMDD` strings | One per layer of `hh` and `hv`, in order. |

Sites: `west` and `east` (Central Kalimantan, tracks `125` ascending and `061` descending), `oki` (South Sumatra, tracks `010` ascending and `119` descending).

Both stacks of a site are on the same grid, the one of the ascending track, so they line up pixel for pixel. Their date lists differ. Each stack has a `.json` file next to it with its dates, source granules and grid. Loading code is in `pipeline/radar/README.md`.

Release tag: `data-v1`, then `data-v2` and so on. Never replace a file inside a published tag.

## 2. Map layers (tracks 2 and 3 write; tracks 4 and 5 read)

GeoTIFF, float32, NaN for no data, on the same grid as the stack it came from. Written to `pipeline/out/layers/` and attached to the release.

| File | Owner | Meaning |
|---|---|---|
| `drydown_<site>_<track>.tif` | 2 | Change in HH against intact forest, last two passes before the rain minus first two, on 250 m blocks. Decibels. |
| `dried_<site>.tif` | 2 | 1 where the dry-down is beyond the noise floor on both orbits, else 0. |
| `recovery_hh_<site>.tif`, `recovery_hv_<site>.tif` | 2 | Change across the first rain, in decibels. |
| `fire_days_<site>.tif` | 3 | Number of distinct days with a 2026 fire detection within 200 m. |
| `peat_official_<site>.tif`, `peat_cifor_<site>.tif` | 3 | 1 on mapped peat, else 0. Local use only: not committed and not put in a release until the licence is confirmed. |
| `rain_daily_<site>.json` | 3 | `{ "YYYY-MM-DD": mm }`, box mean. |
| `canals_osm_<site>.geojson` | 3 | OpenStreetMap waterways. |

## 3. Numbers (tracks 2, 3 and 5 write; tracks 4 and 6 read)

`pipeline/out/validation.json`, one entry per number:

```json
{
  "two_orbit_agreement_250m": { "value": 0.0, "unit": "Spearman r", "site": "west", "status": "exploratory", "made_by": "pipeline/checks/two_orbit.py" }
}
```

`status` is `exploratory` until track 5 has rerun it, then `final`. The app and the slides show only `final` numbers.

## 4. App files (track 4 owns; committed)

- `app/public/layers/<id>.png`: a layer drawn as an image, in Web Mercator.
- `app/public/layers/layers.json`: the list the app reads.

```json
[
  { "id": "dried_west", "title": "Dried beyond the noise floor", "url": "layers/dried_west.png",
    "bounds": [113.6, -3.2, 114.2, -2.4], "date": null, "unit": "dB", "legend": "sequential",
    "source": "NISAR L2 GCOV, ASF DAAC" }
]
```

`bounds` is west, south, east, north in degrees. A layer that changes over the season has one entry per date with `date` set to `YYYY-MM-DD`.

Track 4 owns the script that turns a GeoTIFF from section 2 into a PNG and an entry in `layers.json`.
