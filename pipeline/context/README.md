# Context layers (track 3)

Fire, rain, peat and canals: the layers that say what the radar signal means and where it matters.

| Script | Source | Writes | Needs |
|---|---|---|---|
| `pull_firms.py`, `fire_layers.py` | NASA FIRMS, VIIRS and MODIS | `fire_days_<site>.tif`, `fire_days_1km_<site>.tif`, `fire_dates_<site>.json`, and with `--dry-until` `fire_before_rain_<site>.tif`, `fire_before_rain_1km_<site>.tif` | `FIRMS_MAP_KEY` in the environment |
| `rain.py` | NASA GPM IMERG Late daily | `rain_daily_<site>.json`, the last dry day | Earthdata login with GES DISC approved |
| `peatmap.py` | PEATMAP (Xu et al. 2018), CC BY 4.0 | `peat_peatmap_<site>.tif`, `peat_peatmap_<site>.geojson` | nothing |
| `peat.py` | Indonesia Ministry of Agriculture peat map, via Global Forest Watch | `peat_official_<site>.tif`, local only, as a cross-check | nothing |
| `canals.py` | OpenStreetMap | `canals_osm_<site>.geojson`, `canal_distance_<site>.tif` | nothing |

Run them all with `WITH_CONTEXT=1 SKIP_PULL=1 pipeline/run_all.sh`, or one at a time (each file starts with its command).

## Rules of this folder

- **Two peat layers, one of them public.** `peat_peatmap_*` comes from PEATMAP, which is CC BY 4.0, so it can be released and shown in the app with its citation. `peat_official_*` has no stated licence and never leaves your machine. On our sites the two agree on 99% (west) and 98% (east) of the grid, so the public one is used for every number.
- **Low-confidence fire detections are dropped.** A detection is a satellite pixel of 0.4 to 1 km or more, so each one marks every cell within half its own pixel size. A second layer marks everything within 1 km. These are active-fire detections, not burnt area.
- **Fire after the rain is kept apart.** `fire_days` counts every detection from 1 May to the day of the pull. `fire_before_rain` counts only those on or before the last dry day, so a comparison of burnt and unburnt land on the pass after the rain is not mixed with fire that came later.
- **The last dry day is read from the rainfall record by a fixed rule,** not chosen by eye: the day before the first day of 5 mm or more that opens a 5-day window of 25 mm or more, after the driest 30 days.
- **OpenStreetMap is incomplete here.** A place far from a mapped canal may still be drained.

## Still to do

The CIFOR peat map (Gumbricht et al. 2017) as a second opinion on the boundary, repeat-fire layers from earlier years, and the coherence burn flag. The recovery and fusion steps still read `fire_days`; their owners switch to `fire_before_rain` where the comparison is after the rain.
