# Dry Season Waltz (working title)

Team Garugons, NASA Space Apps Challenge 2026, challenge "Dancing with the SARs".

**Status: being built this weekend (14 and 15 November 2026). Nothing here is final yet.**

## What it is

An open web map that uses the first dry season seen by the NASA-ISRO NISAR radar over Borneo's peatlands to show three things:

1. **Dry.** Where the land dried out, pass by pass, through cloud and smoke.
2. **Burn.** Where it burned.
3. **Rewet.** What the rain brought back, and what it did not.

It is a screening map that shows where to look. It does not measure the water table or predict fire.

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
| Dry-down | `pipeline/drying/drydown.py`, `per_pass.py` | How far HH fell over the dry season, and one layer per pass |
| Noise floor | `pipeline/drying/noise_floor.py` | What counts as a real fall, on both orbits |
| Recovery | `pipeline/recovery/recovery.py` | What the rain brought back in HH and in HV |
| Checks | `pipeline/drying/selfcheck.py`, `sensitivity.py` | Tests for artefacts and for our own choices |
| App data | `pipeline/drying/series.py`, `app/scripts/` | Files the web map reads |

Outputs land in `pipeline/out/`. The numbers are in `pipeline/out/validation.json`. The built files are also attached to the releases `data-v1`, `data-v3` and `data-v4`.

## Data

| Dataset | Agency | Source |
|---|---|---|
| NISAR L2 GCOV backscatter (HH, HV) and L2 GUNW coherence | NASA and ISRO | Alaska Satellite Facility DAAC, https://search.asf.alaska.edu |
| GPM IMERG daily rainfall | NASA | GES DISC, https://disc.gsfc.nasa.gov |
| FIRMS active fire detections (VIIRS, MODIS) | NASA | https://firms.modaps.eosdis.nasa.gov |
| Waterways | OpenStreetMap contributors | https://www.openstreetmap.org |

## Use of Super Intelligence (SI)

This project is built with SI coding assistants working under each team member's direction. Code files written with SI assistance say so in their first comment line, and `submission/SI_USE.md` records where SI was used.

## Licence

MIT. See `LICENSE`.
