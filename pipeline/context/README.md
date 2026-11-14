# Context layers (track 3)

Fire, rain, peat and canals: the layers that say what the radar signal means and where it matters.

| Script | Source | Writes | Needs |
|---|---|---|---|
| `pull_firms.py`, `fire_layers.py` | NASA FIRMS, VIIRS and MODIS | `fire_days_<site>.tif`, `fire_dates_<site>.json` | `FIRMS_MAP_KEY` in the environment |
| `rain.py` | NASA GPM IMERG Late daily | `rain_daily_<site>.json`, the last dry day | Earthdata login with GES DISC approved |
| `peat.py` | Indonesia Ministry of Agriculture peat map, via Global Forest Watch | `peat_official_<site>.tif`, local only | nothing |
| `canals.py` | OpenStreetMap | `canals_osm_<site>.geojson`, `canal_distance_<site>.tif` | nothing |

Run them all with `WITH_CONTEXT=1 SKIP_PULL=1 pipeline/run_all.sh`, or one at a time (each file starts with its command).

## Rules of this folder

- **The peat layer never leaves your machine.** Its licence is not confirmed, so `peat_official_*` is not committed and not put in a release. Anyone can rebuild it with `peat.py`.
- **Low-confidence fire detections are dropped,** and a detection marks every cell within 200 m.
- **The last dry day is read from the rainfall record by a fixed rule,** not chosen by eye: the day before the first day of 5 mm or more that opens a 5-day window of 25 mm or more, after the driest 30 days.
- **OpenStreetMap is incomplete here.** A place far from a mapped canal may still be drained.

## Still to do

The CIFOR peat map (Gumbricht et al. 2017) as a second opinion on the boundary, repeat-fire layers from earlier years, and the coherence burn flag.
