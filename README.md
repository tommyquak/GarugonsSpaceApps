# Dry Season Waltz

Team Garugons, NASA Space Apps Challenge 2026, challenge "Dancing with the SARs".

Built on 14 and 15 November 2026.

## What it is

An open web map that uses the first dry season seen by the NASA-ISRO NISAR radar over Borneo's peatlands to show three things:

1. **The fall.** Where the radar echo fell over the dry season, pass by pass, through cloud and smoke.
2. **Fire.** Where NASA's FIRMS detected fire.
3. **The first rain.** Where the echo rose again on the first pass after the rain, and where it did not.

It is a screening map that shows where to look. It does not measure the water table, predict fire or recommend an intervention. Part way through we asked a Super Intelligence (SI) reviewer to audit the work, and changed it: see `docs/AUDIT.md` and `docs/LIMITS.md`.

## Repository layout

| Folder | What is in it |
|---|---|
| `pipeline/` | Python that turns NISAR files into map layers and a file of validation numbers |
| `app/` | The web map |
| `submission/` | Project page text, slides and the record of SI use |
| `docs/` | Data contract, limits and references |
| `tools/` | The team's agent message board |

For how the team works, see `PLAN.md` and `AGENTS.md`.

## Run it yourself

Everything shown in the app is produced by the code in `pipeline/`, from NASA's archive to the numbers.

```
pip install -r requirements.txt

# quick: start from the radar stacks we publish (about 600 MB), a few minutes
gh release download data-v1 --repo tommyquak/GarugonsSpaceApps --dir pipeline/out/stacks
SKIP_PULL=1 pipeline/run_all.sh

# full: pull the NISAR windows yourself (needs a NASA Earthdata login in ~/.netrc), a few hours
pipeline/run_all.sh
```

| Step | Code | What it does |
|---|---|---|
| Pull | `pipeline/radar/pull_gcov.py` | Reads only the part of each NISAR L2 GCOV granule that covers a site |
| Stack | `pipeline/radar/build_stack.py` | HH and HV at 50 m, in decibels, both orbits on one grid |
| Reference | `pipeline/drying/reference.py`, `baseline.py` | Deep intact forest as the yardstick, and the scene-wide shift of each pass |
| The fall | `pipeline/drying/drydown.py`, `per_pass.py` | How far HH fell over the dry season, and one layer per pass |
| Forest spread | `pipeline/drying/noise_floor.py` | The 5th percentile of change in the reference forest, on both orbits |
| After the rain | `pipeline/recovery/recovery.py` | What changed in HH and in HV on the first pass after the rain |
| Checks | `pipeline/drying/selfcheck.py`, `sensitivity.py` | Tests for artefacts and for our own choices |
| App data | `pipeline/drying/series.py`, `app/scripts/` | Files the web map reads |

Tests for the processing code: `python -m pytest pipeline/tests`.

Outputs land in `pipeline/out/`. The numbers are in `pipeline/out/validation.json`; the copy the app and the slides read is `app/public/validation.json`. The built files are attached to the data releases, the latest being `data-v9`.

## Data

| Dataset | Agency | Source |
|---|---|---|
| NISAR L2 GCOV backscatter (HH, HV) and L2 GUNW coherence | NASA and ISRO | Alaska Satellite Facility DAAC, https://search.asf.alaska.edu |
| GPM IMERG daily rainfall | NASA | GES DISC, https://disc.gsfc.nasa.gov |
| FIRMS active fire detections (VIIRS, MODIS) | NASA | https://firms.modaps.eosdis.nasa.gov |
| Waterways | OpenStreetMap contributors | https://www.openstreetmap.org |
| PEATMAP peat extent, CC BY 4.0 | Xu, Morris, Liu and Holden 2018, University of Leeds | https://doi.org/10.5518/252 |
| Sentinel-2 cloudless 2016 mosaic (basemap), CC BY 4.0 | EOX, from Copernicus Sentinel data (ESA) | https://cloudless.eox.at |
| Blue Marble imagery (basemap option) | NASA GIBS | https://earthdata.nasa.gov/gibs |
| VIIRS daily true colour, `VIIRS_SNPP_CorrectedReflectance_TrueColor` (ground look in the place card) | NASA GIBS, Suomi NPP | https://earthdata.nasa.gov/gibs |

## Use of Super Intelligence (SI)

This project is built with SI coding assistants working under each team member's direction. Code files written with SI assistance say so in their first comment line, and `submission/si_use/` records where SI was used, one file per team member.

## Licence

MIT. See `LICENSE`.
