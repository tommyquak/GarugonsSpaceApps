# Project page

The text of the project page, field by field. Every result is a `final` entry in `app/public/validation.json`.

## 1. Project name

Dry Season Waltz

## 2. High-level summary

Drainage makes peat more vulnerable to fire. In Central Kalimantan, thousands of kilometres of canals dug in the 1990s still drain the peat, and in dry years it burns and sends haze across the region, Singapore included. Restoring it starts with knowing which ground is drying, but cloud and smoke can hide that ground from optical satellites during the dry season.

We built Dry Season Waltz, an open web map for peat restoration teams of what NISAR, the new NASA and ISRO L-band radar, saw over these peatlands in its first dry season. Radar sees through cloud and smoke. We followed the radar echo of the land through the 2026 dry season in three steps: where it fell, where NASA detected fire, and what changed after the first rain. A fall counts only where two orbits looking from opposite sides both saw it, measured against closed forest.

What a team can do with it: open the map, play the season, and download a list of 1 km blocks to visit first, each with its coordinates and the radar and fire evidence behind it, ready for a GIS or a GPS. NISAR adds what fire records cannot: where the echo had still not recovered after the first rain. It runs on free NASA data. It is a screening map that says where to look. It has not been checked on the ground yet, so it does not measure the water table, predict fire or choose a remedy.

## 3. Link to project demo

Seven slides, with recordings of the app playing inside them:
https://docs.google.com/presentation/d/1vesg1eznCPqGbcpzD-PjqL7T5cbiIpfgGebKZvpY5_A/edit?usp=sharing

## 4. Link to final project

- App: https://tommyquak.github.io/GarugonsSpaceApps/
- Code and data: https://github.com/tommyquak/GarugonsSpaceApps

## 5. Detailed project description

### What it does

- **One-look map.** Colour shows how far the HH radar echo fell between mid July and mid October 2026, on 250 m blocks, relative to deep intact forest. Fire detections are shown on their own, in red.
- **Play the season.** A slider steps through every NISAR pass on both orbits, with a "whole season" view.
- **Click a place.** A chart shows HH and HV at that spot for the whole season, with daily rain and the dates fire was detected.
- **Where to check.** 1 km blocks labelled by what was seen (fire detected; fell and still low after the rain; fell and came back), drawn as 3D columns and as a ranked list that exports to CSV and GeoJSON. Each block shows the evidence behind its label.
- **How it decides.** Every class has a written rule, drawn as a graph from the data source to the answer, with its thresholds. We call it the ontology, and the pipeline and the app read it from the same file.
- **Field assessment.** Three pages to print: a map of the blocks, the evidence, and a table of blocks to visit, with a box to tick.
- **What is new.** A change counts only when two orbits looking from opposite sides both saw it, and every label on the map can be traced, rule by rule, to the measurement behind it. NISAR adds what the fire record cannot: whether the echo recovered after the first rain.
- **Shows its limits.** A panel lists what the map cannot tell you, from `docs/LIMITS.md`, and the audit and our response are published with the code.

### Who it is for, and what they can do with it

Field teams, peat restoration agencies and researchers who need to choose where on a peat landscape to look first, and who today often get a cloud-free picture of it only after the season is over.

1. **Take the list.** Every 1 km square comes with its coordinates and the evidence behind it, as CSV and GeoJSON that open in a GIS or on a GPS.
2. **Visit the top of the list first.** Start where the echo stayed weak after the rain, and where fire was detected. Measure the water depth and look at the canals.
3. **The field team decides whether to act.** The remedy is the agency's, not ours. Indonesia's peat restoration programme works by rewetting (blocking canals with dams, filling them in, drilling deep wells), replanting, and supporting local livelihoods.
4. **Look again next season.** NISAR is built to come back every 12 days. If the agency blocks a canal, it could use the same map next season to check how the radar echo changes there. We have not tested this.

### How it works

1. **Radar stacks.** NISAR L2 GCOV backscatter (HH and HV) for an ascending dawn track and a descending dusk track, averaged to 50 m and stacked by date. Both orbits are on one grid.
2. **A rain-free start.** A fixed rule applied to NASA’s daily rainfall sets the earliest eligible start pass seven days after the last wet day before the driest 30-day stretch (`pipeline/season.py`). This reduces the influence of recent rain on the baseline.
3. **A yardstick.** Calibration and weather shift a whole scene from pass to pass. We measure that shift on deep intact peat swamp forest, at least 4 km from any edge, and remove it from HH.
4. **The fall.** HH late in the dry season minus HH at its start, on 250 m blocks. We count mapped area where HH fell by 1 dB or more on both orbits, which look from opposite sides at different times of day.
5. **After the rain.** The change from the late dry season to the first pass after the rain, in HH, and HV as measured compared between places with and without fire detections.

### What we found

- Between mid July and mid October 2026, HH fell by 1 dB or more on both orbits, relative to deep forest, across about 755 km² of mapped peat in the west and about 292 km² in the east. The study areas overlap. The two orbits ranked the locations of the fall similarly (Spearman ρ = 0.83 west and 0.87 east).
- The fall follows the calendar. In an exact test that tried every other way of sorting the same passes into an early and a late group, no other sorting gave a fall as large as the real order (one-sided p = 0.010 on the dawn orbit and 0.002 on the dusk orbit, in both areas).
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

### Tools and technologies

- **Pipeline:** Python 3.11 with numpy, scipy, h5py, rasterio, pyproj and matplotlib. It reads the NISAR files over the network from NASA's archive at the Alaska Satellite Facility, a block at a time, so nothing has to be downloaded whole.
- **App:** TypeScript, Vite and MapLibre GL JS, served as a static site from GitHub Pages. No server, and no commercial map tiles.
- **Checks:** We ran 80 automated tests covering the pipeline and its independent checks. GitHub Actions runs the pipeline tests and builds the app on every pull request.
- **One file of numbers.** Every figure on this page and on the slides is read from `app/public/validation.json`, and the app lists them with their status. A number is marked final only after a second team member has reproduced it independently.
- **Slides:** built by a script, which reads its numbers from that same file.

### How we built it

Six people over one weekend, in one repository, each with an SI coding assistant. The work was split into parts: radar stacks, the fall, the change after the rain, fire and context layers, the app, checks and limits, story and submission. The assistants passed work between team members on a shared message board in the repository, and every change went in through a pull request with automated checks. Part way through we asked an SI reviewer to audit the work adversarially. It found that our first start date came just after rain; we moved the start, and the result got smaller. The audit and our response are in `docs/AUDIT.md`.

## 6. Use of Super Intelligence (SI)

Yes. We used Super Intelligence (SI) coding assistants throughout the weekend, each under the direction of one team member. They wrote and tested the pipeline and app code, ran the analysis, drafted the documentation, this page and the slides, and passed work between team members on a shared message board. An SI reviewer was asked to audit the work adversarially part way through; what it found and what we changed are published in `docs/AUDIT.md`. Team members decided the approach, checked the results and chose what to claim.

Three things on the site were made with SI: the illustrative control room on the entry view and the animated schematic of the radar echoes, which are both labelled where they appear, and the narration of the opening story, which is synthetic speech in a copy of a team member's own voice. Every code file written with SI assistance says so in its first comment line, and `submission/si_use/` lists each use, one file per team member. No SI-made picture is presented as data: every map layer, figure and number is computed by the code in the repository from NASA, ISRO and other open data.

## 7. NASA data

- **NISAR L2 GCOV** (NASA and ISRO), from the Alaska Satellite Facility DAAC, https://search.asf.alaska.edu. The core of the project: L-band HH and HV backscatter on a dawn and a dusk orbit, June to November 2026. These measurements show where the radar echo fell and how it changed after rain.
- **NISAR L2 GUNW** (NASA and ISRO), same archive. The 12-day interferometric pairs, used for their coherence in one exploratory check, and the basis of the planned subsidence layer.
- **GPM IMERG Late daily rainfall**, version 07, NASA GES DISC. [NASA dataset record](https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergdl-07). Sets the dry season: a fixed rule reads its start and its end from the daily rain, and it is the rain shown under every chart.
- **FIRMS active fire detections** (VIIRS and MODIS), https://firms.modaps.eosdis.nasa.gov. Where and when fire was detected, on peat and off it. Together with the peat boundary, detections determine which blocks qualify as “fire detected on peat”. We compare detections from 2015, 2019 and 2023 with those in 2026 to identify places with repeat detections.
- **NASA GIBS imagery**, https://nasa-gibs.github.io/gibs-api-docs/. The place card shows dated true-colour imagery from VIIRS on Suomi NPP. Slide 3 uses VIIRS on NOAA-20 for its optical image of the study area, taken on the same day as the NISAR radar image. Blue Marble is a basemap option.

## 8. Space agency partner and other data, and references

Space agency partner: ISRO, with NASA, for NISAR.

- OpenStreetMap contributors, waterways and base map, https://www.openstreetmap.org
- Sentinel-2 cloudless 2016 by EOX, the default base map (contains modified Copernicus Sentinel data 2016), CC BY 4.0, https://s2maps.eu
- Peat boundary: PEATMAP (Xu et al. 2018), CC BY 4.0. [Dataset record, DOI 10.5518/252](https://archive.researchdata.leeds.ac.uk/251/). The main peat area and fire estimates use this boundary. PEATMAP and the Indonesian Ministry of Agriculture peat map draw on the same national mapping. Estimated peat area in the eastern box is sensitive to which boundary is used. The official map has no stated licence and is not redistributed.
- Jaenicke, Englhart and Siegert 2011, monitoring the effect of restoration measures in Indonesian peatlands by radar satellite imagery. DOI 10.1016/j.jenvman.2010.09.029. [PubMed record](https://pubmed.ncbi.nlm.nih.gov/20971549/)
- Hess, Melack and Simonett 1990, Radar detection of flooding beneath the forest canopy: A review. DOI 10.1080/01431169008955095. [Publisher record](https://doi.org/10.1080/01431169008955095)
- Kim et al. 2017, Characterizing hydrologic changes of the Great Dismal Swamp using SAR/InSAR. DOI 10.1016/j.rse.2017.06.009. [Author’s copy at SMU (PDF)](https://www.smu.edu/-/media/site/dedman/academics/departments/earthsciences/pdf/kim/020_kim_gds_peatland_rse_2017.pdf)
- Dadap et al. 2019, satellite soil moisture observations predict burned area in Southeast Asian peatlands. DOI 10.1088/1748-9326/ab3891. [MIT repository](https://dspace.mit.edu/entities/publication/9eeb57d2-e8fe-4774-b956-642bb51013c9)
- Hooijer et al. 2012, Subsidence and carbon loss in drained tropical peatlands, Biogeosciences 9, 1053 to 1071. [DOI 10.5194/bg-9-1053-2012](https://doi.org/10.5194/bg-9-1053-2012). Cited for the future plan only.
- Tay et al. 2025, Satellite radar advances carbon emissions accountability over tropical peat, Communications Earth and Environment 6, 971. [DOI 10.1038/s43247-025-02926-6](https://doi.org/10.1038/s43247-025-02926-6). Cited for the future plan only; its data are not used.

- Takashi Hirano, daily groundwater level in drained and undrained peat swamp forest near Palangka Raya, 2013 to 2018, figshare, [DOI 10.6084/m9.figshare.22321129](https://doi.org/10.6084/m9.figshare.22321129), CC BY 4.0. Used to fit the rainfall-driven water-table model shown beside the radar.
- World Bank 2016, The Cost of Fire: an economic analysis of Indonesia's 2015 fire crisis. Koplitz et al. 2016, Environmental Research Letters 11, 094023. Government of Indonesia, Regulation 57 of 2016 on peat ecosystems. Jong 2018, Mongabay, on the Mega Rice Project. UN DESA, on Indonesia's peat restoration measures. Links for each are in `submission/IMPACT.md`.
- Photographs in the opening story and on the slides, from Wikimedia Commons: DenY Krisbiyantoro (CC BY-SA 4.0); Josh Estey / AusAID and Ruanda Agung Sugardiman / AusAID (CC BY 2.0). Author, source and changes for each are in `app/public/story/CREDITS.md`.
- Software: MapLibre GL JS (BSD-3-Clause), Vite, TypeScript, IBM Plex Sans (SIL OFL); Python with numpy, scipy, h5py, fsspec, rasterio, pyproj, matplotlib, pillow, python-pptx and pytest.
- SI tools: coding assistants (code, analysis, documentation, the audit), an image generator (the illustrative control room), and a text-to-speech service (the story narration).

Every source with its licence is in `submission/LICENCES.md`. The full list, with a confidence tag for each claim, is in `docs/REFERENCES.md`.
