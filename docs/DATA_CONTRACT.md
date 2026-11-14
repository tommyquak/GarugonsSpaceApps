# Data contract

The file formats the tracks hand to each other. If you need to change one, change this file in the same PR and tag the owners it affects on the board.

Nothing in this file is committed to git except the small app files in section 5. Stacks and layers are attached to a GitHub release.

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
| `hh_<site>_<track>_<YYYYMMDD>.tif` | 2 | One per radar pass, for the season slider. HH on that pass minus HH at the start of the season (mean of the first two passes), scene-wide shift removed, on 250 m blocks. Decibels. Negative means darker than at the start. |
| `dried_<site>.tif` | 2 | 1 where the dry-down is beyond the noise floor on both orbits, else 0. |
| `recovery_hh_<site>_<track>.tif`, `recovery_hv_<site>_<track>.tif` | 2 | Change across the first rain, in decibels: first pass after the rain minus the last two dry passes. One per orbit that has a pass after the rain. |
| `recovery_left_hh_<site>_<track>.tif`, `recovery_left_hv_<site>_<track>.tif` | 2b | What the rain did not bring back, in decibels: first pass after the rain minus the start of the season (mean of the first two passes). Negative means still darker than in June. One per orbit that has a pass after the rain. |
| `fire_days_<site>.tif` | 3 | Number of distinct days with a 2026 fire detection within 200 m. |
| `peat_peatmap_<site>.tif`, `peat_peatmap_<site>.geojson` | 3 | 1 on mapped peat, else 0, and its outline in lon/lat. From PEATMAP (Xu et al. 2018, doi 10.5518/252), CC BY 4.0: may be released and shown with that citation. This is the peat layer every number uses. |
| `peat_official_<site>.tif`, `peat_cifor_<site>.tif` | 3 | Other peat maps as cross-checks. Local use only: no stated licence, so not committed and not released. |
| `canals_osm_<site>.geojson`, `canal_distance_<site>.tif` | 3 | Canals, drains and ditches from OpenStreetMap (ODbL), and metres to the nearest one. |
| `rain_daily_<site>.json` | 3 | `{ "YYYY-MM-DD": mm }`, box mean. |

## 3. Numbers (tracks 2, 3 and 5 write; tracks 4 and 6 read)

`pipeline/out/validation.json`, one entry per number:

```json
{
  "two_orbit_agreement_250m": { "value": 0.0, "unit": "Spearman r", "site": "west", "status": "exploratory", "made_by": "pipeline/checks/two_orbit.py" }
}
```

`status` is `exploratory` until track 5 has rerun it, then `final`. The app and the slides show only `final` numbers.

## 4. Time series for the click chart (track 1 writes; track 4 reads)

Two files per site in `pipeline/out/series/`, attached to the release: `series_<site>.json` and `series_<site>.bin`.

The grid is regular in longitude and latitude, so the app finds a cell without any map projection: `col = floor((lon - west) / cell_deg)`, `row = floor((north - lat) / cell_deg)`.

```json
{
  "site": "west", "bounds": [113.6, -3.2, 114.3, -2.4], "cell_deg": 0.0025, "rows": 320, "cols": 280,
  "scale": 0.12, "offset": -30.0, "nodata": 0,
  "bands": [ { "track": "125", "pol": "hh", "date": "2026-06-22" } ]
}
```

`series_<site>.bin` is unsigned bytes, one `rows * cols` image per entry of `bands`, in that order, each stored row by row from the north-west corner. Decibels = `byte * scale + offset`. A byte of 0 means no data. Values are backscatter with the scene-wide shift removed, averaged over about 250 m.

`fire_dates_<site>.json` (track 3 writes, optional, same folder): the days with a fire detection in each cell of the grid of `series_<site>.json`, as `{ "<row * cols + col>": ["YYYY-MM-DD", ...] }`. A cell without a detection has no key. The chart shows these days under the radar lines.

## 5. App files (track 4 owns; committed)

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
