# Context layers (track 3)

Fire, rain, peat and canals: the layers that say what the radar signal means and where it matters.

| Script | Source | Writes | Needs |
|---|---|---|---|
| `pull_firms.py`, `fire_layers.py` | NASA FIRMS, VIIRS and MODIS | `fire_days_<site>.tif`, `fire_days_1km_<site>.tif`, `fire_dates_<site>.json`, and with `--dry-until` `fire_before_rain_<site>.tif`, `fire_before_rain_1km_<site>.tif` | `FIRMS_MAP_KEY` in the environment |
| `repeat_fire.py` | NASA FIRMS for earlier seasons (2015, 2019, 2023), pulled with `pull_firms.py` into `data/firms_history/<site>/<year>/` | `fire_years_<site>.tif`, and how much of the 2026 fire fell on land that had fire before | `FIRMS_MAP_KEY` for the pull |
| `pull_gunw.py`, `burn_flag.py` | NISAR L2 GUNW coherence (ASF), checked against NASA FIRMS | `coh_drop_<site>_<track>.tif`, `burn_flag_<site>_<track>.tif`, and how well the flag matches fire detections | Earthdata login in `~/.netrc`, with ASF authorised |
| `rain.py` | NASA GPM IMERG Late daily | `rain_daily_<site>.json`, the last dry day | Earthdata login with GES DISC approved |
| `peatmap.py` | PEATMAP (Xu et al. 2018), CC BY 4.0 | `peat_peatmap_<site>.tif`, `peat_peatmap_<site>.geojson` | nothing |
| `peat.py` | Indonesia Ministry of Agriculture peat map, via Global Forest Watch | `peat_official_<site>.tif`, local only, as a cross-check | nothing |
| `peat_cifor.py` | CIFOR tropical peatland map (Gumbricht et al. 2017), modelled at 231 m | `peat_cifor_<site>.tif`, local only, and its agreement with PEATMAP | `py7zr` once, to unpack the 41 MB download |
| `canals.py` | OpenStreetMap | `canals_osm_<site>.geojson`, `canal_distance_<site>.tif` | nothing |

Run them all with `WITH_CONTEXT=1 SKIP_PULL=1 pipeline/run_all.sh`, or one at a time (each file starts with its command).

## Rules of this folder

- **Two peat layers, one of them public.** `peat_peatmap_*` comes from PEATMAP, which is CC BY 4.0, so it can be released and shown in the app with its citation. `peat_official_*` has no stated licence and never leaves your machine. On our sites the two agree on 99% (west) and 98% (east) of the grid, so the public one is used for every number. They draw on the same national mapping, so that agreement is not an independent check.
- **The independent peat map does not confirm the boundary.** CIFOR's map is modelled from hydrology, satellite soil moisture and landforms, not from the national survey. On our grids it agrees with PEATMAP about as often as two unrelated maps would (`peat_map_agreement_cifor_*` against `peat_map_agreement_cifor_chance_*`). Redrawn on CIFOR peat, the fall of 1 dB or more moves from 755 to 646 km2 in the west and from 292 to 574 km2 in the east (`fell_1db_km2_on_cifor_peat_*`). CIFOR is a coarse model that its authors matched to soil profiles 65% of the time, so this does not say PEATMAP is wrong; it says the peat boundary is a real source of uncertainty, largest in the east. Its terms conflict (CC BY 4.0 on the dataset page, written permission for commercial use in the file), so `peat_cifor_*` stays local.
- **Low-confidence fire detections are dropped.** A detection is a satellite pixel of 0.4 to 1 km or more, so each one marks every cell within half its own pixel size. A second layer marks everything within 1 km. These are active-fire detections, not burnt area.
- **Fire after the rain is kept apart.** `fire_days` counts every detection from 1 May to the day of the pull. `fire_before_rain` counts only those on or before the last dry day, so a comparison of burnt and unburnt land on the pass after the rain is not mixed with fire that came later.
- **Most 2026 fire fell where fire had been before.** Against the 2015, 2019 and 2023 seasons (July to November, same detection rules), 86% of the 2026 fire on western peat was on land that had fire in at least one of them, while 47% of western peat had (`fire_repeat_share_*` against `fire_earlier_share_*`). In the east 81% of peat had fire before, so the comparison says less there. This is where fire returned, not why: open drained peat, where fire concentrates, may explain both. Earlier seasons were seen by fewer satellites, so earlier fire is if anything undercounted.
- **The radar sees the burns on its own.** In 12-day NISAR coherence, pairs that span a fire detection drop by a median 0.16 to 0.27 against none in cells without fire. On peat, 49 to 72% of the land with fire is flagged; 86 to 94% of the flagged land had fire within 1 km, against 39 to 71% of all land; and the largest drop falls in the pair that spans the fire for 88 to 96% of it, against 19 to 23% by luck (`coh_flag_timing_*` against `coh_flag_timing_chance_*`). The two orbits, looking from opposite sides at dawn and dusk, flag the same land (`coh_flag_two_orbit_overlap_*`, Spearman 0.62 west and 0.80 east on peat). A drop is any change of the ground, not only fire: along the river in the west box the flag also marks floodplain with no fire, likely changing water. Pairs longer than 12 days (late July to mid August on both tracks) are left out, so fire in that gap is not tested.
- **The last dry day is read from the rainfall record by a fixed rule,** not chosen by eye: the day before the first day of 5 mm or more that opens a 5-day window of 25 mm or more, after the driest 30 days.
- **OpenStreetMap is incomplete here.** A place far from a mapped canal may still be drained.

## Still to do

The recovery and fusion steps still read `fire_days`; their owners switch to `fire_before_rain` where the comparison is after the rain.
