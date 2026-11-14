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
