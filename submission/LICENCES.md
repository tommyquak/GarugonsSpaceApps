# Licence check

Track 6. Checked on 14 November 2026, 22:00 SGT, against the repository at that time, the twelve releases and the live site. The rule is in `AGENTS.md` section 6: everything we ship is free and open, and anything under a non-commercial or unstated licence is linked and cited, never committed.

**Result: nothing found that we may not ship.** Three small gaps were found and fixed in the same change (listed at the end). One point needs the team's decision (the narration, below).

## Our own work

| What | Licence | Where it says so |
|---|---|---|
| All code in `pipeline/`, `app/`, `submission/`, `tools/` | MIT | `LICENSE`, `README.md` |
| Derived layers, numbers and figures in the releases and `app/public/` | MIT, with the attribution of each source below | Release notes, `README.md` |

## Data

| Source | Licence | In the repo or a release as | Credit shown |
|---|---|---|---|
| NISAR L2 GCOV and GUNW, NASA and ISRO, from ASF DAAC | NASA open data | Stacks and layers derived from it (`data-v1` onwards); `app/public/story/radar.jpg` | Map credits, About, `README.md` |
| FIRMS active fire (VIIRS, MODIS), NASA | NASA open data | Fire layers; `firms_2023_west_east.zip` in `data-v9` | Map credits, About |
| GPM IMERG daily rainfall, NASA GES DISC | NASA open data | `rain_daily_<site>.json` | About, `docs/REFERENCES.md` |
| NASA GIBS imagery (VIIRS true colour, Blue Marble) | NASA open data | `smoke.jpg`, `optical.jpg`; tiles fetched by the app at run time | Story credits, map credits |
| PEATMAP, Xu et al. 2018 | CC BY 4.0 | `peat_peatmap_<site>.tif` and `.geojson` (`data-v7`, `data-v9`) | Map credits, About, release notes |
| OpenStreetMap waterways | ODbL 1.0 | `canals_osm_<site>.geojson`, `canal_distance_<site>.tif` | "OpenStreetMap contributors" in the map credits and release notes |
| Hirano groundwater record | CC BY 4.0 | `gauge_daily.json` (`data-v9`) | `pipeline/hydro/README.md`, the water-table figure |
| Sentinel-2 cloudless 2016 by EOX | CC BY 4.0 | Not stored: tiles fetched at run time | Map credits |

## Pictures and sound

| File | Maker | Licence | Credit shown |
|---|---|---|---|
| `app/public/story/fire.jpg`, `burnt.jpg` | DenY Krisbiyantoro, Wikimedia Commons | CC BY-SA 4.0 | In the story, and `app/public/story/CREDITS.md` with the changes made |
| `canal.jpg`, `open.jpg` | Josh Estey, AusAID, Wikimedia Commons | CC BY 2.0 | Same |
| `forest.jpg` | Ruanda Agung Sugardiman, AusAID, Wikimedia Commons | CC BY 2.0 | `CREDITS.md` (not shown in the story at present) |
| `app/src/intro/room.png`, and `app_room.jpg` in `figures-v3` | Made with SI | Ours, MIT | Labelled on the page as an illustrative scene made with SI, and wherever it is shown |
| `explainer.gif`, `explainer.mp4` | Made with SI assistance, by code in this repo | Ours, MIT | Carries a visible SI line and says it is a schematic |
| `app/public/story/voice/beat-1.mp3` to `beat-7.mp3` | Made with a text-to-speech service, in a synthetic copy of a team member's own voice | Ours | **Not labelled where it plays.** Logged in `submission/si_use/tommyquak.md` as a draft to be replaced. See the open point below |
| App recordings and screenshots in `figures-v3` | Recorded from our own app | Ours, MIT | Release notes |

The photographs were resized and re-compressed and are otherwise unchanged; `CREDITS.md` records that, with author, licence and source for each. They stay under CC BY-SA 4.0; our MIT licence does not cover them.

## Software and services

| What | Licence | Note |
|---|---|---|
| MapLibre GL JS | BSD-3-Clause | Bundled in the app |
| IBM Plex Sans (`@fontsource/ibm-plex-sans`; Google Fonts in the HTML deck) | SIL OFL 1.1 | Bundled in the app; fetched by the HTML deck |
| Vite, TypeScript | MIT, Apache-2.0 | Build tools only |
| numpy, scipy, h5py, fsspec, aiohttp, requests, certifi, rasterio, pyproj, matplotlib, pillow, py7zr, python-pptx, pytest | BSD, MIT, Apache-2.0, MPL-2.0 (certifi), LGPL (py7zr) and similar open licences | Installed by the user from `requirements.txt`; none is copied into the repo |
| OpenStreetMap tiles (a base map option) | ODbL data, tile usage policy | Fetched at run time, credited in the map |

## Used locally, never committed

| What | Why it stays out |
|---|---|
| Indonesian Ministry of Agriculture peat polygons | No stated licence. Compared with PEATMAP on a local machine only; the agreement is reported as a number |
| CIFOR tropical wetlands map (Gumbricht et al. 2017) | Downloaded by `pipeline/context/peat_cifor.py` when a user runs it; the raster is not redistributed, only the numbers that come from it |

No file of either is in the repository or in any release (all twelve release file lists were read for this check).

## Found and fixed in this change

1. `python-pptx` was missing from `requirements.txt`, though `submission/build_slides.py` needs it.
2. Two hook scripts in `.claude/hooks/` did not start with the SI line that every code file carries.
3. This file did not exist.

## Open point for the team

The opening story's narration is synthetic speech and nothing on the page says so. `AGENTS.md` asks for a visible mark on SI-made images and video and does not mention sound. Before submission, one of three: replace the clips with a recorded voice, say on the page that the voice is synthetic, or switch the sound off. Until then the SI statement names it.
