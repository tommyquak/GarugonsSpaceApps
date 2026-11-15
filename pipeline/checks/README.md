# Track 5: independent checks

**Use the same release as the map.** The app’s data-v9 uses a rain-free July start; data-v3 includes earlier, wetter passes. Their metrics have the same names but different observation periods. Keep their JSON files separate and use only rows marked `final` from the matching handoff. Run from the repository root with its Python dependencies installed.

The checked-in [validation.json](../../app/public/validation.json) is the app and slides handoff. The corrected data-v9 recovery files were reissued on 14 November. The result contains 475 upstream entries (the 357 that were checked, then exploratory entries added afterwards: 14 from `pipeline/context/peat_cifor.py`, 24 from `pipeline/context/repeat_fire.py` and 80 from `pipeline/context/burn_flag.py`) and 136 final Track 5 entries. The 24 repeat-fire entries were rebuilt by Track 5 from the released rasters and NASA's detection files and are final too. To list the exact final keys, use the filter below.

The data-v9 dry-season comparison uses a 16 July start pass on track 125 and 12 and 24 July on track 061. The first qualifying rain was on 26 October. The recovery comparison uses 28 October on track 061 and 1 November on track 125.

The original HV rebound layers in data-v9 included a forest baseline shift of +0.167 dB on track 061 and −0.034 dB on track 125 at both sites. The 14 November replacement uses HV as measured. Track 5 checked the release checksums and reproduced all eight whole-site and driest-tenth medians from the radar stacks. For the whole western site on track 061 the median changed from +0.1282 dB to −0.0388 dB. [Correction record](https://github.com/tommyquak/GarugonsSpaceApps/issues/1#issuecomment-6873030852)

To reproduce the **v9 app handoff** from public releases:

```sh
repo=tommyquak/GarugonsSpaceApps
layers=pipeline/out/v9
stacks=pipeline/out/v9-stacks
gh release download data-v1 -R "$repo" -D "$stacks" -p '*_125.npz'
gh release download data-v5 -R "$repo" -D "$stacks" -p '*_061.npz'
gh release download data-v9 -R "$repo" -D "$layers" -p 'drydown_*' -p 'dried_*' -p 'baseline_*' -p reference_west.tif -p 'rain_daily_*' -p 'fire_days_west.tif' -p 'fire_days_east.tif' -p 'recovery_hh_*' -p 'recovery_hv_*' -p validation.json
gh release download data-v7 -R "$repo" -D "$layers" -p 'peat_peatmap_*.tif'
python -m pytest -q pipeline/tests pipeline/checks
python -m pipeline.checks.run --layers "$layers" --stacks "$stacks" --seed "$layers/validation.json" --output pipeline/out/validation.json --repeat
```

For the **original v3 audit**, use all four data-v1 stacks, the data-v3 layers, the orbit-specific data-v5 rebound layers and a separate output file. Use the data-v5 validation seed for the original exploratory recovery run. For a dated recovery rerun add data-v6 daily rain to the layer directory and use its validation seed. The v9 descending stack has an additional pass; its baseline must not be mixed with v1.

Each check may also run separately with `--check orbit|forest|shuffle|recovery|peat`. The modules behind them are `two_orbit.py`, `forest.py`, `date_shuffle.py`, `recovery.py` and `peat_split.py`; `run.py` is the runner, `common.py` holds what they share, and `prepare_official.py` prepares the official peat map on a local machine. A normal run writes exploratory rows. `--verify` compares them at published precision, including the full key set. `--repeat` compares two complete calculations at full precision before writing. Failure preserves the existing output. Each invocation preserves unrelated keys and the read-only seed. Use a fresh output path when switching seeds and a single writer during an upstream rebuild.

| Key suffix (after site and, where applicable, orbit) | What it measures |
|---|---|
| `orbit_pearson`, `orbit_spearman`, `orbit_blocks`, `orbit_driest_tenth_overlap` | Correlations and overlap on the common radar footprint. The overlap denominator is the lowest floor(n/10) ascending blocks. Ties break in row-major order. |
| `forest_p05`, `forest_p50`, `forest_p95` | Spread in the shared west forest used for correction. A difference above 0.001 dB from a supplied upstream percentile keeps that percentile exploratory. |
| `date_shuffle_*` | The acquisition dates and cutoff are in the notes. The exact one-sided fraction is `tail_count / pairing_count` (both under the `date_shuffle_` prefix); the shared writer rounds the displayed fraction to four decimals. |
| `recovery_<track>_<pol>_*` | Response after rain in HH or HV versus drying on the opposite orbit, on the intersection of all three valid footprints. The runner checks the released last-dry day against the daily rainfall series before promotion. Alternatively supply Track 3’s date(s) and handoff via `--rain-onset` and `--rain-source`. Only one later pass per orbit. The corrected v9 rebound files reproduce the HV medians calculated from the radar stacks. Earlier downloads had a forest offset. |
| `dried_peat_<map>_*`, `fire_peat_<map>_*` | Areas in km² and fractions of valid on-peat or off-peat ground; multiply a share by 100 for a percentage. The drying flag is the forest-p05 mask, not the map’s stronger 1 dB criterion. Unknown mask coverage has its own area. |

PEATMAP (Xu et al., [dataset DOI](https://doi.org/10.5518/252), CC BY 4.0) is the public boundary. Official and CIFOR rasters are separate, optional local cross-checks. Do not rename one map as another or release the official raster. For a local official check, first use Track 3’s `pipeline/context/peat.py` to save the ministry polygons locally. Then rebuild and compare the mask with the saved polygons:

```sh
layers=pipeline/out/v9
python pipeline/context/peat.py --site west --layers "$layers" --keep pipeline/out/local-official
python pipeline/checks/prepare_official.py --site west --layers "$layers" \
  --geojson pipeline/out/local-official/peat_official_west.geojson \
  --output "$layers/peat_official_west.tif"
```

Repeat with `--site east` and its matching GeoJSON. The preparation script makes read-only `returnIdsOnly`, count, and source-ID crosswalk queries to WRI/GFW; the service object ID (`objectid_1`) is checked separately from each source polygon's `objectid`. It refuses mismatched IDs or a rebuilt mask that differs from the locally generated Track 3 mask. It writes to a temporary file and replaces the local mask only after all checks pass, so the runner can consume the verified raster at its expected path. Pixel centres outside that site's query box, and pixels already nodata in the local mask, remain nodata; zero means no polygon in the mapped layer within the query box, not field-verified absence of peat. Source GeoJSON and outputs stay local because the service licence is unstated. Treat the two boxes separately: their areas overlap. Missing inputs produce no numeric claims for that map.

To extract exactly what the app and slides can display:

```sh
jq -r 'to_entries[] | select((.key | startswith("track5_")) and .value.status == "final") | .key' pipeline/out/validation.json
```
