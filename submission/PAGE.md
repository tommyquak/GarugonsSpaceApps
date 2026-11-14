# Project page draft

Track 6, owner Reagan. Rewritten after the independent audit (`docs/AUDIT.md`): every claim here is on its list of what we can still claim. Every `[v: key]` is a number to be filled from `pipeline/out/validation.json` (release `data-v9` or later) once that entry is marked `final`. Nothing here is submitted until Tommy presses submit.

## 1. Project name

Dry Season Waltz (working title; the team has not confirmed it)

## 2. High-level summary

Every dry season, drained peatland in Borneo is at its most flammable, some of it burns, and the smoke reaches cities across the region, Singapore included. Optical satellites often lose sight of the ground just then, behind cloud and then smoke. We built an open web map that follows NISAR's first dry season over these peatlands in three steps: where the radar echo of the land fell, where fire was detected, and what changed after the first rain. NISAR's L-band radar sees through cloud and smoke and reaches into the forest canopy every 12 days. We measure the fall of its HH echo against deep intact forest, keep only what two orbits looking from opposite sides both see, and show it as a map anyone can play through the season. It is a screening map of where to check on the ground. It does not measure the water table or predict fire.

## 3. Link to project demo

To be added: seven slides with animated GIFs (public link).

## 4. Link to final project

- App: https://tommyquak.github.io/GarugonsSpaceApps/
- Code and data: https://github.com/tommyquak/GarugonsSpaceApps

## 5. Detailed project description

### What it does

- **One-look map.** Colour shows how far the HH radar echo fell between mid July and late October 2026, on 250 m blocks, relative to deep intact forest. Fire detections are shown on their own, in red.
- **Play the season.** A slider steps through every NISAR pass on both orbits, with a "whole season" view.
- **Click a place.** A chart shows HH and HV at that spot for the whole season, with daily rain and the dates fire was detected.
- **Where to check.** 1 km blocks labelled by what was seen (fire detected; fell and still low after the rain; fell and came back), drawn as 3D columns and as a ranked list that exports to CSV and GeoJSON. Each block shows the evidence behind its label.
- **Shows its limits.** A panel lists what the map cannot tell you, from `docs/LIMITS.md`, and the audit and our response are published with the code.

### How it works

1. **Radar stacks.** NISAR L2 GCOV backscatter (HH and HV) for an ascending dawn track and a descending dusk track, averaged to 50 m and stacked by date. Both orbits are on one grid.
2. **A rain-free start.** The season starts at the first passes with no heavy rain before them, chosen by a rule from NASA's daily rainfall (`pipeline/season.py`), so the fall is not just the surface losing the last rain.
3. **A yardstick.** Calibration and weather shift a whole scene from pass to pass. We measure that shift on deep intact peat swamp forest, at least 4 km from any edge, and remove it from HH.
4. **The fall.** HH late in the dry season minus HH at its start, on 250 m blocks. A block counts if it fell by 1 dB or more on both orbits, which look from opposite sides at different times of day.
5. **After the rain.** The change from the late dry season to the first pass after the rain, in HH, and HV as measured compared between places with and without fire detections.

### What we found

- Between mid July and late October 2026, HH fell by 1 dB or more, relative to deep forest, on [v: fell_1db_km2_on_peat_west] km2 of mapped peat in the west box and [v: fell_1db_km2_on_peat_east] km2 in the east. The two orbits agree on where: Spearman r = [v: track5_west_orbit_spearman] in the west and [v: track5_east_orbit_spearman] in the east, and the agreement holds inside single land-cover classes.
- Deep intact forest is a steady yardstick in the dry season: the 95th percentile of its change over the season is [v: reference_drydown_p95_125] dB on the dawn orbit and [v: reference_drydown_p95_061] dB on the dusk orbit.
- Forest edges fall too: about [v: selfcheck_forest_edge_median_125] dB within 250 m of a forest edge, reaching zero only about 4 km inside.
- Within days of the first heavy rain, HH on the land that fell rose by about [v: recovery_hh_median_rebound_west_125] dB on the dawn orbit and [v: recovery_hh_median_rebound_west_061] dB on the dusk orbit, and not on the pass before the rain.
- Fire was detected on [v: fire_share_on_peat_west] of mapped peat in the west box and [v: fire_share_on_peat_east] in the east. After the rain, HV on peat with fire detections sat [v: recovery_hv_left_fire_minus_no_fire_on_peat_west_125] dB below peat without them, the same sign on both orbits at both sites.

### The physics, and the polarisations

At L-band the wave passes through leaves and reaches the ground. A wetter surface sends back a stronger echo: as open peat dries, HH falls. Closed forest barely changed over the season, so it is the yardstick. HV comes mostly from the woody vegetation, though it also responds to moisture, so the two are not separate "water" and "vegetation" channels. What we use is the contrast: on peat where fire was detected, HV stayed lower after the rain than on peat where it was not.

### What we do not see, and what we do not claim

- Nothing here has been checked against the ground. Our tests are internal: two orbits agree, deep forest holds still, HH rises with the rain. They show the signal is real, not what it means in centimetres of water. The public water-level records for this landscape end before NISAR began. About sixty dipwell visits to 30 of our blocks, in the late dry season and after the first rain, would calibrate the map or show where it is wrong (`submission/IMPACT.md`).
- A fall in HH is not a measured drop in the water table, and no block is a recommendation to block a canal.
- We do not claim to find fire-prone ground ahead of fire. Inside drained land, an early fall did not separate later fire from no fire.
- The passes after the rain come from a later NASA processing release than the dry passes, so the size of the rise is uncertain by a few tenths of a decibel (`docs/AUDIT.md`, finding 3). Each orbit has one pass after the rain so far.
- Burnt and cleared land also changes the echo. Fire detections are shown separately and buffered by each sensor's own pixel size.
- Five months of NISAR cannot show peat subsidence. That needs years.
- Peat fires are not the only fires in Indonesia. The map shows fire off peat as well.
- The full list is in `docs/LIMITS.md`, and the audit with our response is in `docs/AUDIT.md`.

### What NISAR could do next

With two to three years of passes, the same stacks support subsidence mapping by interferometry over whole peat domes, and a record of every dry season to set against wet years. The pipeline takes any bounding box, so the same map can be built for another peatland.

### Who it is for

Field teams and researchers who need to choose where on a peat landscape to look first in a dry season, and who today often get a cloud-free picture of it only after the season is over.

## 6. Use of Super Intelligence (SI)

Team to confirm before submission. Draft: We used SI coding assistants throughout the weekend, under each team member's direction, to write and test the pipeline and app code, to run the analysis, to draft documentation and this page, and to coordinate work through a shared message board. An SI reviewer was also asked to audit the work adversarially; its findings and our response are published in `docs/AUDIT.md`. Team members decided the approach, reviewed the results and chose what to claim. Code files written with SI assistance say so in their first line, and `submission/si_use/` lists each use. SI-made images and video carry a visible watermark.

## 7. NASA data

- NISAR L2 GCOV (NASA and ISRO), Alaska Satellite Facility DAAC, https://search.asf.alaska.edu
- GPM IMERG daily rainfall, NASA GES DISC, https://disc.gsfc.nasa.gov
- FIRMS active fire detections (VIIRS and MODIS), https://firms.modaps.eosdis.nasa.gov
- NASA GIBS imagery: Blue Marble for a basemap option, and VIIRS daily true colour (`VIIRS_SNPP_CorrectedReflectance_TrueColor`, Suomi NPP) for the dated ground look in the place card, https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api

## 8. Space agency partner and other data, and references

- OpenStreetMap contributors, waterways and base map, https://www.openstreetmap.org
- Sentinel-2 cloudless 2016 by EOX, the default base map (contains modified Copernicus Sentinel data 2016), CC BY 4.0, https://s2maps.eu
- Peat boundary: PEATMAP, Xu et al. 2018, CC BY 4.0, doi 10.5518/252. Every peat number uses it. It agrees with the Indonesian Ministry of Agriculture peat map on [v: peat_map_agreement_west] of cells in the west box and [v: peat_map_agreement_east] in the east; the two draw on the same mapping, so this is not an independent check. The official map has no stated licence and is not redistributed.
- Jaenicke, Englhart and Siegert 2011, monitoring the effect of restoration measures in Indonesian peatlands by radar satellite imagery, doi 10.1016/j.jenvman.2010.09.029
- Hess, Melack and Simonett 1990, radar detection of flooding beneath the forest canopy, doi 10.1080/01431169008955095
- Kim et al. 2017, L-band backscatter and groundwater in forested peat, doi 10.1016/j.rse.2017.06.009
- Dadap et al. 2019, satellite soil moisture observations predict burned area in Southeast Asian peatlands, doi 10.1088/1748-9326/ab3891

Track 5 keeps the full list with a confidence tag for each claim in `docs/REFERENCES.md`.
