# Project page

The text of the project page, field by field. Every result is a `final` entry in `app/public/validation.json`.

## 1. Project name

Dry Season Waltz (working title; the team has not confirmed it)

## 2. High-level summary

Every dry season, drained peatland in Borneo is at its most flammable, some of it burns, and the smoke reaches cities across the region, Singapore included. Optical satellites often lose sight of the ground just then, behind cloud and then smoke. We built an open web map that follows NISAR's first dry season over these peatlands in three steps: where the radar echo of the land fell, where fire was detected, and what changed after the first rain. NISAR's L-band radar sees through cloud and smoke and reaches into the forest canopy. Each orbit has a nominal 12-day repeat cycle, with gaps in the available observations. We measure the fall of its HH echo against deep intact forest, keep only what two orbits looking from opposite sides both see, and show it as a map anyone can play through the season. It is a screening map of where to check on the ground. It does not measure the water table or predict fire.

## 3. Link to project demo

To be added: seven slides with animated GIFs (public link).

## 4. Link to final project

- App: https://tommyquak.github.io/GarugonsSpaceApps/
- Code and data: https://github.com/tommyquak/GarugonsSpaceApps

## 5. Detailed project description

### What it does

- **One-look map.** Colour shows how far the HH radar echo fell between mid July and mid October 2026, on 250 m blocks, relative to deep intact forest. Fire detections are shown on their own, in red.
- **Play the season.** A slider steps through every NISAR pass on both orbits, with a "whole season" view.
- **Click a place.** A chart shows HH and HV at that spot for the whole season, with daily rain and the dates fire was detected.
- **Where to check.** 1 km blocks labelled by what was seen (fire detected; fell and still low after the rain; fell and came back), drawn as 3D columns and as a ranked list that exports to CSV and GeoJSON. Each block shows the evidence behind its label.
- **Shows its limits.** A panel lists what the map cannot tell you, from `docs/LIMITS.md`, and the audit and our response are published with the code.

### How it works

1. **Radar stacks.** NISAR L2 GCOV backscatter (HH and HV) for an ascending dawn track and a descending dusk track, averaged to 50 m and stacked by date. Both orbits are on one grid.
2. **A rain-free start.** A fixed rule applied to NASA’s daily rainfall sets the earliest eligible start pass seven days after the last wet day before the driest 30-day stretch (`pipeline/season.py`). This reduces the influence of recent rain on the baseline.
3. **A yardstick.** Calibration and weather shift a whole scene from pass to pass. We measure that shift on deep intact peat swamp forest, at least 4 km from any edge, and remove it from HH.
4. **The fall.** HH late in the dry season minus HH at its start, on 250 m blocks. We count mapped area where HH fell by 1 dB or more on both orbits, which look from opposite sides at different times of day.
5. **After the rain.** The change from the late dry season to the first pass after the rain, in HH, and HV as measured compared between places with and without fire detections.

### What we found

- Between mid July and mid October 2026, HH fell by 1 dB or more on both orbits, relative to deep forest, across about 755 km² of mapped peat in the west and about 292 km² in the east. The study areas overlap. The two orbits ranked the locations of the fall similarly (Spearman ρ = 0.83 west and 0.87 east).
- In the western reference forest used to correct the radar baseline, the 95th percentile of the HH change was +0.27 dB at dawn and +0.37 dB at dusk. At western forest edges, the median dawn change was −0.4 dB for locations 50 to under 250 m inside the edge.
- In western blocks where HH fell by 1 dB or more on both orbits, the median echo rose 1.15 dB on the first dawn pass after the rain and 1.12 dB on the first dusk pass. Each orbit observed the rebound once.
- Among mapped peat pixels with radar coverage on both orbits, active-fire detection footprints covered about 37% in the west and 61% in the east. In western peat blocks where HH fell by 1 dB or more on both orbits, the median HV change from the dry-season start to the first dawn pass after rain was 0.54 dB lower in blocks with a fire detection than in those without one. The groups use the full study-period fire record, so the comparison cannot establish when fire affected a block.

### The physics, and the polarisations

At L-band the wave passes through thin vegetation and reaches the ground on open peat; under closed forest the ground contributes little. On open ground a drier surface sends back a weaker echo, so HH falls, and clearing and standing water change it too. Closed forest is the yardstick: it barely changed over the season. HV comes mostly from the woody vegetation, though it also responds to moisture, so the two are not separate "water" and "vegetation" channels. What we use is the contrast: on peat where fire was detected, HV stayed lower after the rain than on peat where it was not.

### What we do not see, and what we do not claim

- Nothing here has been checked against the ground. Our tests are internal: two orbits agree, closed forest barely changes, HH rises with the rain. They show the change is on the ground and repeatable, not what it means in centimetres of water. The public water-level records for this landscape end before NISAR began. About sixty dipwell visits to 30 of our blocks, in the late dry season and after the first rain, would calibrate the map or show where it is wrong (`submission/IMPACT.md`).
- A fall in HH is not a measured drop in the water table, and no block is a recommendation to block a canal.
- We do not claim to find fire-prone ground ahead of fire. Inside drained land, an early fall did not separate later fire from no fire.
- The passes after the rain come from a later NASA processing release than the dry passes, so the size of the rise is uncertain by a few tenths of a decibel (`docs/AUDIT.md`, finding 3). Each orbit has one pass after the rain so far.
- Burnt and cleared land also changes the echo. Fire detections are shown separately and buffered by each sensor's own pixel size.
- One season of NISAR cannot show peat subsidence. That needs years.
- Peat fires are not the only fires in Indonesia. The map shows fire off peat as well.
- The full list is in `docs/LIMITS.md`, and the audit with our response is in `docs/AUDIT.md`.

### What NISAR could do next

With two to three years of observations, we could test whether the phase of NISAR’s 12-day interferometric pairs (GUNW) can show long-term peat subsidence, beside the seasonal change in HH. We already pull those pairs and use their coherence in an exploratory check. The current HH and HV backscatter maps do not measure subsidence. Field studies of drained peat and field-tested L-band interferometry motivate this next step (Hooijer et al. 2012; Tay et al. 2025). The pipeline accepts a bounding box. Applying it to a second peatland remains untested.

### Who it is for

Field teams and researchers who need to choose where on a peat landscape to look first in a dry season, and who today often get a cloud-free picture of it only after the season is over.

## 6. Use of Super Intelligence (SI)

Team to confirm before submission. Draft: We used SI coding assistants throughout the weekend, under each team member's direction, to write and test the pipeline and app code, to run the analysis, to draft documentation and this page, and to coordinate work through a shared message board. An SI reviewer was also asked to audit the work adversarially; its findings and our response are published in `docs/AUDIT.md`. Team members decided the approach, reviewed the results and chose what to claim. Code files written with SI assistance say so in their first line, and `submission/si_use/` lists each use. SI-made images and video carry a visible watermark.

## 7. NASA data

- NISAR L2 GCOV (NASA and ISRO), Alaska Satellite Facility DAAC, https://search.asf.alaska.edu
- GPM IMERG Late daily rainfall, version 07, NASA GES DISC. [NASA dataset record](https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergdl-07)
- FIRMS active fire detections (VIIRS and MODIS), https://firms.modaps.eosdis.nasa.gov
- NASA GIBS imagery: Blue Marble for a basemap option, and VIIRS daily true colour (`VIIRS_SNPP_CorrectedReflectance_TrueColor`, Suomi NPP) for the dated ground look in the place card, https://nasa-gibs.github.io/gibs-api-docs/

## 8. Space agency partner and other data, and references

- OpenStreetMap contributors, waterways and base map, https://www.openstreetmap.org
- Sentinel-2 cloudless 2016 by EOX, the default base map (contains modified Copernicus Sentinel data 2016), CC BY 4.0, https://s2maps.eu
- Peat boundary: PEATMAP (Xu et al. 2018), CC BY 4.0. [Dataset record, DOI 10.5518/252](https://archive.researchdata.leeds.ac.uk/251/). Every peat number uses it. PEATMAP and the Indonesian Ministry of Agriculture peat map draw on the same national mapping. Estimated peat area in the eastern box is sensitive to which boundary is used. The official map has no stated licence and is not redistributed.
- Jaenicke, Englhart and Siegert 2011, monitoring the effect of restoration measures in Indonesian peatlands by radar satellite imagery. DOI 10.1016/j.jenvman.2010.09.029. [PubMed record](https://pubmed.ncbi.nlm.nih.gov/20971549/)
- Hess, Melack and Simonett 1990, Radar detection of flooding beneath the forest canopy: A review. DOI 10.1080/01431169008955095. [Publisher record](https://doi.org/10.1080/01431169008955095)
- Kim et al. 2017, Characterizing hydrologic changes of the Great Dismal Swamp using SAR/InSAR. DOI 10.1016/j.rse.2017.06.009. [Author’s copy at SMU (PDF)](https://www.smu.edu/-/media/site/dedman/academics/departments/earthsciences/pdf/kim/020_kim_gds_peatland_rse_2017.pdf)
- Dadap et al. 2019, satellite soil moisture observations predict burned area in Southeast Asian peatlands. DOI 10.1088/1748-9326/ab3891. [MIT repository](https://dspace.mit.edu/entities/publication/9eeb57d2-e8fe-4774-b956-642bb51013c9)
- Hooijer et al. 2012, Subsidence and carbon loss in drained tropical peatlands, Biogeosciences 9, 1053 to 1071. [DOI 10.5194/bg-9-1053-2012](https://doi.org/10.5194/bg-9-1053-2012). Cited for the future plan only.
- Tay et al. 2025, Satellite radar advances carbon emissions accountability over tropical peat, Communications Earth and Environment 6, 971. [DOI 10.1038/s43247-025-02926-6](https://doi.org/10.1038/s43247-025-02926-6). Cited for the future plan only; its data are not used.

The full list, with a confidence tag for each claim, is in `docs/REFERENCES.md`.
