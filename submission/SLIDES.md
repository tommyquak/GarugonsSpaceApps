# Slide outline

**A first full deck is built** (covering track 6 for Reagan, at Tommy's request, Sat 19:30): `app/public/slides/index.html`, live at https://tommyquak.github.io/GarugonsSpaceApps/slides/. It follows the seven-slide order agreed on issue #36 (the radar-under-forest slide dropped; the season and "Where to check" as two app slides) and reads every number from `validation.json` when it opens. Arrow keys or the Back and Next buttons page through it; printing it gives a seven-page PDF. Reagan: it is yours to change. The outline below is the earlier plan, kept for reference.

Seven slides, the demo limit. Track 6, owner Reagan. Rewritten after the independent audit (`docs/AUDIT.md`): every claim is on its list of what we can still claim. Every `[v: key]` is filled from `pipeline/out/validation.json` (release `data-v9` or later) once the entry is `final`; until then the slide shows the key, never a typed number. Figures come from Tommy's `figures-v1` release; GIFs are recorded from the live app. Any SI-made image carries a visible "Made with SI" watermark and a line in its maker's file in `si_use/`.

The thread through all seven: the dry season in three beats, **fall, fire, rain**, seen by a radar that does not stop for cloud or smoke.

## 1. Title

- **Dry Season Waltz** (working title), Team Garugons, "Dancing with the SARs".
- One line: NISAR's first dry season over Borneo's peat, in three beats.
- Visual: the one-look map of the west box with the peat outline, full bleed (`figures-v1`).

## 2. The problem

- Drained peat is at its most flammable in the dry season, some of it burns, and the haze reaches cities across the region.
- Optical satellites often lose the ground exactly then: cloud first, then smoke.
- Peat fires are not the only fires in Indonesia. We show fire off peat too.
- Visual: an optical scene lost under cloud or smoke beside the NISAR pass from the same week (NASA GIBS, credited).

## 3. How the radar sees the ground under the forest

- L-band passes through the leaves. HH carries a strong ground-to-trunk bounce, which weakens as the surface dries (Hess et al. 1990; Kim et al. 2017).
- HV comes mostly from the woody vegetation, but it also responds to moisture: the two are not separate "water" and "vegetation" channels.
- We measure against deep intact forest, from a rain-free start, and keep only what both orbits see.
- Visual: a simple diagram of the two echoes (not in the repo yet; ask Tommy, or draw it, with a watermark if SI-made).

## 4. The one-look map (the demo)

- GIF from the app: the season slider from mid July to November, the fall in sand to brown deepening pass by pass, then HH rising after the rain; fire in red.
- Colour is how far HH fell against deep intact forest. It is not a water-table depth.
- Caption: on mapped peat, HH fell by 1 dB or more on [v: fell_1db_km2_on_peat_west] km2 in the west box and [v: fell_1db_km2_on_peat_east] km2 in the east.

## 5. The evidence

Three beats, one row each:

- **Fall.** The two orbits look from opposite sides at dawn and dusk, and agree on where HH fell: Spearman r = [v: track5_west_orbit_spearman] (west) and [v: track5_east_orbit_spearman] (east), also inside single land-cover classes. Deep forest holds still: 95th percentile of its change [v: reference_drydown_p95_125] dB.
- **Fire.** Fire was detected on [v: fire_share_on_peat_west] of mapped peat in the west box and [v: fire_share_on_peat_east] in the east, buffered by each sensor's pixel size, and off peat too.
- **Rain.** Within days of the first heavy rain, HH rose by about [v: recovery_hh_median_rebound_west_125] dB (dawn) and [v: recovery_hh_median_rebound_west_061] dB (dusk), and not on the pass before. After the rain, HV on peat with fire detections sat [v: recovery_hv_left_fire_minus_no_fire_on_peat_west_125] dB below peat without.
- Visual: the season curve with rain (`figures-v1`), or a GIF of the click chart on a block where fire was detected and HV stayed low.

## 6. The limits

- A screening map of where to check. It does not measure the water table, find fire-prone ground ahead of fire, or recommend blocking any canal.
- Not yet checked on the ground. Public water-level records end before NISAR began; about sixty dipwell visits would calibrate it or prove it wrong.
- The passes after the rain come from a later NASA processing release than the dry ones, so the size of the rise is uncertain by a few tenths of a decibel. One pass after the rain per orbit so far.
- Forest edges fall too: about [v: selfcheck_forest_edge_median_125] dB within 250 m of an edge.
- We asked an independent reviewer to attack the work, and published what it found and what we changed (`docs/AUDIT.md`).
- Visual: the app's limits panel.

## 7. What comes next

- Ground truth first: the sixty-visit field protocol in `submission/IMPACT.md`.
- Years of NISAR passes: subsidence by interferometry over whole peat domes, and every dry season set against wet years.
- The pipeline takes any bounding box: another peatland is one command away.
- Links: the app (the "Where to check" view and ranked list), the code, the data releases (QR code).

## Still to decide

- The name (mentor Q&A Sat 20:00).
- Slides or a 30-second video (confirm Sun 14:00). The outline above works for both: slide 4's GIF is the video.
- Whether slide 3's diagram is drawn by Tommy or by us.
