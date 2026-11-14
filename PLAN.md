# Weekend plan

Sat 14 Nov 09:00 to Sun 15 Nov 23:59 SGT. Owners and folders are in `AGENTS.md` section 3. File formats are in `docs/DATA_CONTRACT.md`.

## What we are building

An open web map that uses NISAR's first dry season over Borneo's peatlands to show three things: where the land dried, where it burned, and what the rain did not bring back. A small Python pipeline turns NISAR files into the map layers and one file of validation numbers.

- **Study area:** Sebangau to Kahayan, Central Kalimantan. NISAR track 125 ascending (dawn) and track 061 descending (dusk), June to November 2026.
- **Second site, if time allows:** Ogan Komering Ilir, South Sumatra. Tracks 010 ascending and 119 descending.
- **The opening screen:** one map where dried peat is coloured, burnt land is black and steady land is grey.

This plan is a starting point. Read it, challenge it and change it.

## First hour, everyone

1. Accept the repo invitation, clone, run `gh auth login`, then `tools/board whoami`.
2. Read `AGENTS.md`, this file and `docs/DATA_CONTRACT.md`.
3. Post on the board: your track, and anything you disagree with in the plan.
4. Check your tools: Python 3.11 or later with numpy, scipy, h5py, rasterio, pyproj and matplotlib; Node 20 or later for the app.

Only track 1 needs a NASA Earthdata login. Everyone else works from the stacks that track 1 publishes as a release.

## The six tracks

| Track | Owner | Builds | Done when | If it slips |
|---|---|---|---|---|
| 1. Radar data and stacks. Critical path. | Tommy | NISAR brightness (HH and HV) for both orbits over the study box and the intact reference forest, plus 12-day coherence pairs. Converted to decibels at 50 m and stacked by date. Published as a release. | Sat 12:00. Both orbit stacks are in the release and list their dates. | Keep one orbit, or shrink to the western box, which is mostly peat. |
| 2. Drying and recovery | Tommy | Intact-forest baseline. Dry-down score on 250 m blocks for both orbits. Noise floor. Recovery after the rain in HH and HV. | Sat 17:00. The one-look map is produced by code in this repo. | Ship the dry-down layer alone and state the recovery as a single-pass result. |
| 3. Fire and context layers | Gabriel | Fire mask, days with fire and repeat fire from NASA FIRMS. Daily rain from GPM IMERG. Peat boundary from both peat maps. Canals from OpenStreetMap. Coherence burn flag if time allows. | Sat 16:00. Layers exported, with areas on and off peat. | Drop the coherence flag and keep fire days. |
| 4. The app | Kalent and Jan Hoe | Web map with a season slider, layer switches, legend, a click-a-place chart with rain and fire dates, and a three-part story mode. Public deploy on GitHub Pages. | Sat 15:00 an empty map is live at a public link. Sat 22:00 real layers are on it. It works on a phone. | Cut story mode, then the click chart. Never cut the slider or the one-look layer. |
| 5. Checks and limits | Anson | Recompute the checks: two-orbit agreement, intact-forest stability, date shuffle, recovery against an independent dry-down, on and off peat. Write the limits panel text. Keep the reference list and the data list. | Sun 12:00. `validation.json` is final and every number on the page and slides comes from it. | Report fewer checks, never unverified numbers. |
| 6. Story and submission | Reagan | The eight project-page fields, seven slides with GIFs, the SI statement and watermarks, the licence check, and every link tested in a private window. | Sun 20:00 page saved. Tommy submits by 22:00. | Slides before video. The page text before either. |

Track 4 has two people because it is the largest build. If a track does not fit you, tell Tommy on the board and he will swap.

## How the tracks fit together

```
1 radar stacks ──> 2 drying layers ──┐
        │                            ├──> 4 app ──> 6 page and slides
        └────────> 3 fire, rain,  ───┤         ^
                     peat, canals    └──> 5 checks (validation.json)
```

- Track 4 does not wait for data. It starts with placeholder layers in the contract format and swaps real ones in.
- Tracks 2, 3 and 5 start from the release that track 1 publishes. Until then they write and test against a small crop.
- Track 6 starts the page text and slide outline on Saturday and fills in numbers on Sunday.

## The three things most likely to sink it

- **Stacks arriving late.** Everything waits on track 1. It publishes a first release as early as possible, even with one orbit.
- **The app arriving late.** Deploy an empty map early, then add layers. A working link on Saturday night is worth more than any extra analysis.
- **Mixing peat and farmland.** Apply the peat boundary from the first step, or the headline numbers will be wrong.

## Cut order if we are behind

Second site, coherence burn flag, story mode, click chart, recovery layer. Never cut: the slider, the one-look map, the two-orbit check, the limits panel.

## Extras, decided at Sat 20:00

Ranked. Attempt one only when the core of its track is done.

1. Second site in South Sumatra, to show the method travels.
2. Sentinel-1 C-band for the same months as a contrast with L-band.
3. A ranked list of the blocks that dried most, click to fly there.
4. Coherence burn flag checked against fire detections.

## Decisions the team still owes

- **Name.** Working title "Dry Season Waltz".
- **Demo format.** Working choice: seven slides with animated GIFs. Confirm Sun 14:00.
