# Slide outline

Seven slides, the demo limit. Track 6, owner Reagan. Every `[v: key]` is filled from `pipeline/out/validation.json` once the entry is `final`; until then the slide shows the key, never a typed number. GIFs are recorded from the live app. Any SI-made image carries a visible "Made with SI" watermark and a line in `SI_USE.md`.

The thread through all seven: the dry season as a dance in three beats, **dry, burn, rewet**, seen by a radar that does not stop for cloud or smoke.

## 1. Title

- **Dry Season Waltz** (working title), Team Garugons, "Dancing with the SARs".
- One line: NISAR's first dry season over Borneo's peat, in three beats.
- Visual: the one-look map of the west box, full bleed.

## 2. The problem

- Drained peat dries every dry season, some of it burns, and the haze reaches cities across the region.
- Optical satellites lose the ground exactly then: cloud first, then smoke.
- Peat fires are not the only fires in Indonesia. We show fire off peat too.
- Visual: an optical scene lost under cloud or smoke beside the NISAR pass from the same week (NASA GIBS, credited).

## 3. How the radar sees wet and dry ground

- L-band passes through the canopy. HH carries the ground-to-trunk bounce: strong when the ground is wet, weaker as it dries.
- HV comes from the woody canopy. It follows vegetation, not water.
- So land that only dried comes back in HH after rain; land that lost its canopy stays low in HV.
- Visual: a simple diagram of the two echoes (drawn by us; watermark if SI-made). Cite Hess et al. 1990 and Kim et al. 2017.

## 4. The one-look map (the demo)

- GIF from the app: the season slider playing June to November, the west box darkening pass by pass, then brightening after the rain.
- Colour is how far HH fell against deep intact forest; black is burnt; grey is steady.
- Caption numbers: [v: dried_both_orbits_km2_west] km2 dried beyond the noise floor on both orbits in the west box; on mapped peat [v: fell_1db_km2_on_peat_west] km2 fell by 1 dB or more.

## 5. The evidence

Three beats, one row each:

- **Dry.** The two orbits look from opposite sides at dawn and dusk, and agree on where land dried: Spearman r = [v: track5_west_orbit_spearman]. Deep forest holds still: noise floor [v: noise_floor_hh_125] and [v: noise_floor_hh_061] dB.
- **Burn.** [v: fell_1db_no_fire_km2_on_peat_west] km2 of the dried peat had no fire nearby; the rest is shown separately, on peat and off it.
- **Rewet.** After the first rain, both orbits see the rebound on their own and their rebound maps agree (r = [v: recovery_hh_two_orbit_r_west_061_125]). HH regained [v: recovery_hh_share_regained_west_125] and [v: recovery_hh_share_regained_west_061] of the fall; HV only [v: recovery_hv_share_regained_west_125] and [v: recovery_hv_share_regained_west_061]. What the rain did not bring back is the story.
- Visual: GIF of the click chart on one strongly dried block, HH and HV with rain and fire dates under it.

## 6. The limits

- A screening map: it shows where to look. It does not measure the water table, subsidence or where fire will start.
- Forest edges dry too: about [v: selfcheck_forest_edge_median_125] dB within 250 m of an edge, zero only about 4 km inside.
- One pass after the rain per orbit so far; the share regained moves by up to [v: recovery_hh_share_regained_sensitivity_west_061] in HH when the choice of passes changes. A placebo (rain pretended one pass sooner) shows no rebound: [v: recovery_hh_share_regained_placebo_west_061].
- Every check that failed, from `docs/LIMITS.md`.
- Visual: the app's limits panel.

## 7. What comes next

- Years of NISAR passes: subsidence by interferometry over whole peat domes, and a dry-down record for every season.
- The pipeline takes any bounding box: a second site in South Sumatra if time allows.
- For people who block canals, patrol for fire or study haze.
- Links: the app, the code, the data releases (QR code).

## Still to decide

- The name (mentor Q&A Sat 20:00).
- Slides or a 30-second video (confirm Sun 14:00). The outline above works for both: slide 4's GIF is the video.
- Which block the slide 5 click chart shows: one that dried, burned and did not come back in HV.
