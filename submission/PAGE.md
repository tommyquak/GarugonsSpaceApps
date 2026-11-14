# Project page draft

First draft, written while covering track 6 for Reagan. It is his to rewrite. Every `[v: key]` is a number to be filled from `pipeline/out/validation.json` once that entry is marked `final`. Nothing here is submitted until Tommy presses submit.

## 1. Project name

Dry Season Waltz (working title; the team has not confirmed it)

## 2. High-level summary

Every dry season, drained peatland in Borneo dries out, some of it burns, and the smoke reaches cities across the region, Singapore included. Optical satellites lose sight of the ground just when it matters, behind cloud and then smoke. We built an open web map that uses the first dry season seen by the NASA-ISRO NISAR radar to follow that dance in three steps: where the land dried, where it burned, and what the first rain brought back. NISAR's L-band radar passes through cloud, smoke and forest canopy every 12 days, and its HH echo falls as the ground under the trees dries. We measure that fall against deep intact forest, keep only what two opposite orbits both see, and show it as a map anyone can play through the season. It is a screening tool: it shows where to look, not how deep the water table is.

## 3. Link to project demo

To be added: seven slides with animated GIFs (public link).

## 4. Link to final project

- App: https://tommyquak.github.io/GarugonsSpaceApps/
- Code and data: https://github.com/tommyquak/GarugonsSpaceApps

## 5. Detailed project description

### What it does

- **One-look map.** Colour shows how far the HH radar echo fell between June and October 2026, on 250 m blocks. Intact forest stays grey.
- **Play the season.** A slider steps through every NISAR pass on both orbits. Drained land darkens pass after pass, then brightens when the rain returns.
- **Click a place.** A chart shows HH and HV at that spot for the whole season.
- **Shows its limits.** A panel lists what the map cannot tell you and which checks it passed or failed.

### How it works

1. **Radar stacks.** NISAR L2 GCOV backscatter (HH and HV) for an ascending dawn track and a descending dusk track, averaged to 50 m and stacked by date. Both orbits are put on one grid.
2. **A yardstick.** Rain and calibration shift a whole scene from pass to pass. We measure that shift on deep intact peat swamp forest, at least 4 km from any edge, and remove it.
3. **Dry-down score.** HH late in the dry season minus HH at its start, on 250 m blocks.
4. **Noise floor and two orbits.** A block counts only if it fell further than the reference forest ever moves, on both orbits. The orbits look from opposite sides at different times of day, so an artefact of one is unlikely to appear in the other.
5. **Recovery.** The change across the first rain, in HH and in HV.

### What we found

- The two orbits agree on where the land dried: r = [v: two-orbit agreement, west] in the west box and [v: two-orbit agreement, east] in the east.
- Deep forest holds still: the noise floor is [v: noise_floor_hh_125] dB and [v: noise_floor_hh_061] dB, and [v: reference_flagged_share] of the reference forest is flagged.
- Forest edges dry too: the fall is about [v: selfcheck_forest_edge_median_125] dB within 250 m of a forest edge and reaches zero only about 4 km inside.
- On mapped peat in the west box, [v: fell_1db_km2_on_peat_west] km2 fell by 1 dB or more; [v: fell_1db_no_fire_km2_on_peat_west] km2 of that had no fire nearby.
- After the first rain, land that had fallen by 1 dB or more regained [v: recovery_hh_share_regained_west_125] of the fall in HH and [v: recovery_hv_share_regained_west_125] in HV.

### The physics, and the polarisations

At L-band the wave passes through leaves and reaches branches, trunks and the ground. HH carries the echo that bounces between ground and trunk, which is strong when the ground is wet and weakens as it dries. HV comes from the woody canopy. So HH follows water and HV follows vegetation: land that only dried recovers in both after rain, while land that lost its canopy to fire or clearing stays low in HV.

### What we do not see, and what we do not claim

- We do not measure the water table or soil moisture in physical units. Colour means the radar echo fell.
- Burnt and cleared land also darkens. The fire layer separates it; without it the map mixes the two.
- Five months of NISAR cannot yet show peat subsidence. That needs years.
- The radar does not predict where fire will start.
- Peat fires are not the only fires in Indonesia. The map shows fire off peat as well.
- Only one pass after the rain exists so far, on one orbit, so the recovery result is a single-pass result.

### What NISAR could do next

With two to three years of passes, the same stacks support subsidence mapping by interferometry over whole peat domes, and a dry-down record for every dry season. The pipeline takes any bounding box, so the same map can be built for another peatland.

### Who it is for

People who block canals, patrol for fire or study haze, and who today have no picture of the dry season on the ground until it is over.

## 6. Use of Super Intelligence (SI)

Team to confirm before submission. Draft: We used SI coding assistants throughout the weekend, under each team member's direction, to write and test the pipeline and app code, to run the analysis, to draft documentation and this page, and to coordinate work through a shared message board. Team members decided the approach, reviewed the results and chose what to claim. Code files written with SI assistance say so in their first line, and `submission/SI_USE.md` lists each use. SI-made images and video carry a visible watermark.

## 7. NASA data

- NISAR L2 GCOV (NASA and ISRO), Alaska Satellite Facility DAAC, https://search.asf.alaska.edu
- GPM IMERG daily rainfall, NASA GES DISC, https://disc.gsfc.nasa.gov
- FIRMS active fire detections (VIIRS and MODIS), https://firms.modaps.eosdis.nasa.gov
- NASA GIBS imagery for the basemap, https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api

## 8. Space agency partner and other data, and references

- OpenStreetMap contributors, waterways and base map, https://www.openstreetmap.org
- Peat boundary: Indonesian Ministry of Agriculture peat map, viewed through Global Forest Watch; and Gumbricht et al. 2017, doi 10.17528/CIFOR/DATA.00058. Linked, not redistributed.
- Jaenicke, Englhart and Siegert 2011, monitoring the effect of restoration measures in Indonesian peatlands by radar satellite imagery, doi 10.1016/j.jenvman.2010.09.029
- Hess, Melack and Simonett 1990, radar detection of flooding beneath the forest canopy, doi 10.1080/01431169008955095
- Kim et al. 2017, L-band backscatter and groundwater in forested peat, doi 10.1016/j.rse.2017.06.009
- Dadap et al. 2019, satellite soil moisture observations predict burned area in Southeast Asian peatlands, doi 10.1088/1748-9326/ab3891

Track 5 keeps the full list with a confidence tag for each claim in `docs/REFERENCES.md`.
