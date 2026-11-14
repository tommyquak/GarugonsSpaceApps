# Limits

What this project can and cannot say. The app shows this file in its Limits panel. It was first written from the findings of an independent audit on 14 Nov 2026 (`docs/AUDIT.md`). Track 5 owns it from here.

## What the map shows, exactly

The colour is how far the L-band HH radar echo fell between a dry start in mid July and mid October 2026, relative to deep intact forest, on 250 m blocks, where two orbits both saw it. It is a change in a radar signal. It is not a measurement of soil moisture or of the water table.

## Limits of the measurement

- **No ground truth.** Nothing here was checked against the ground. No water-level or soil-moisture measurements for 2026 were used, and we found none in public.
- **A fall in HH is not only drying.** Over open and thinly vegetated land HH falls as the surface dries. It also changes with clearing, harvest, standing water and fire, and under dense forest the ground contributes little. The pipeline separates fire detections and nothing else.
- **Forest is zero by definition.** Each pass is shifted so that deep forest does not change. Drying under the forest itself cannot be seen. Measured (`pipeline/drying/by_cover.py`, exploratory): on western peat whose HV marks closed forest, the median HH change is under 0.1 dB and 2% fell by 1 dB on both orbits; on open and thinly vegetated peat the median fall is 0.8 to 1.0 dB and about a third fell. The map is a map of open, drained and degraded peat, which is also where most of the fire was.
- **The start matters.** The first passes of the season came just after rain. Measured from those, 1,349 km2 of western peat fell by 1 dB or more. Measured from the first rain-free passes, chosen by a rule in `pipeline/season.py`, it is 755 km2. We report the second.
- **Thresholds are choices.** The 1 dB fall, the 0.5 dB "still low" level, the 25% fire share and the 1 km distances were set on 14 Nov 2026, the day of the first results, and are not derived from a reference. Moving the fall threshold by a quarter of a decibel moves the area by about a quarter.
- **The 5th percentile is not a noise floor for open land.** Deep forest moves by about 0.3 dB (5th percentile). On open land the two orbits disagree by 0.3 to 0.5 dB, so a fall there is clear from about 0.5 to 0.8 dB, which is why the map starts at 1 dB.
- **The offset comes from one forest.** The scene-wide shift is measured on 650 km2 of forest in the west of one box and applied across both boxes, up to about 130 km away. The east box has almost no deep forest to test it on.
- **Gaps in the record.** The dawn orbit has no pass between 16 July and 21 August, and the dusk orbit none between 24 July and 17 August. "Every 12 days" is the satellite's design, not this record.
- **One instrument.** The two orbits are separate looks by the same radar. They share its calibration and our baseline, so their agreement shows the change is on the ground, not what the change is.

## Limits of the recovery result

- **One pass per orbit after the rain,** taken on or within three days of 20 to 40 mm of rain. Water on vegetation and standing water raise the echo too.
- **A different processing release.** The two passes after the rain were produced by a later NASA processing release than every dry-season pass, and the forest baseline moves most on exactly those passes. The size of the rise is uncertain by about 0.3 to 0.4 dB.
- **"Still low after the rain" is unexplained.** Those blocks tend to be woodier and farther from mapped canals than the ones that came back. We do not know why they stayed low, and we attach no recommendation to them.
- **What does hold:** HH rose by about 1 dB within days of the first rain on both orbits, and not one pass earlier; and after the rain, HV on peat with fire detections sat about half a decibel below peat without them, on both orbits.

## Limits of the fire layer

- **Active fire, not burnt area.** Detections are satellite pixels of 0.4 to 1 km or more. Each is buffered by its own size. Fire under thick smoke or cloud and low smouldering fire in peat can be missed.
- **Fire changes the echo both ways.** Burnt open peat fell less in HH than unburnt open peat, and some burnt land brightened.
- **Peat fires are not the only fires.** Fire was detected on 37% of mapped peat and 30% of the land outside it in the west box.

## Limits of the classes

- **They describe, they do not prescribe.** A class says what was seen and where a field visit would be informative. None of them is a recommendation to block a canal or to intervene.
- **Most classed blocks are "fire detected on peat",** which uses the fire detections and the peat map and no radar.
- **"Agreement" is a count, not a probability.**
- **Canals are context only.** In our data the fall in HH does not change with distance to a mapped canal, and OpenStreetMap is incomplete here.
- **One peat map.** PEATMAP and the official map are the same national mapping, so their 98 to 99% agreement is not an independent check. The one independent map we could test, CIFOR's modelled map (Gumbricht et al. 2017), does not confirm the boundary (`pipeline/context/peat_cifor.py`, exploratory): cell by cell it agrees with PEATMAP on 57% of the west box and 50% of the east, about what two unrelated maps would reach. It is a speckled model output and its authors matched soil profiles 65% of the time, so this does not show PEATMAP is wrong; it shows the peat boundary is a real uncertainty. On CIFOR peat the 1 dB fall covers 646 km2 in the west (755 on PEATMAP) and 574 km2 in the east (292), so the western figure is fairly robust to the choice of map and the eastern one is not.

## Fire-prone ground: no clear result

We tested whether an early fall marked the peat that later burned. Across all western peat, blocks that had fallen by 0.5 dB by the end of August burned later more often (56% against 29%). Inside drained land the difference vanishes: 3 points in the west (95% range minus 9 to plus 18) and minus 9 points in the east (minus 28 to plus 8). The all-peat gap is forest against open land. We make no claim about fire-prone ground.

## A bridge to the ground: weak support, not validation

`pipeline/hydro/` fits a small rainfall-driven model to the published 2013 to 2018 water-table record at two sites near Palangka Raya, tests it on years left out of the fit (it follows the gauge with a correlation of 0.74 to 0.94 and an error of 8 to 26 cm, apart from one half year), and runs it on 2026 rainfall. That modelled water table falls below the 0.4 m limit by July at the forest site and to about 1.3 m by late October. At the drained site the radar's HH moves with it on the dawn orbit (r 0.87 over 10 passes) and less clearly at dusk (0.42 over 11); at the forest site the radar barely moves. Both curves answer the same rain and the passes are few, so this is support for the reading of the signal, not a validation of it. The 2026 water table is modelled, not measured.

## What would test it

- **Water table:** dipwells read on the day of each pass through one dry season, at 40 to 60 blocks spread over the classes and land covers.
- **Surface moisture:** satellite soil moisture products for the same weeks, and a second radar at another wavelength.
- **Fire:** post-season burn scars from optical imagery.
- **Everything:** a second season and a second site.

## Reading the independent Track 5 results

Use the JSON for the map release being shown. The original data-v3 comparison used June/July start passes. Data-v9 uses 16 July on track 125 and 12/24 July on 061, with late passes in October. Whole-site orbit agreement measures repeatability of the radar pattern; it does not identify peat or validate the cause. The west forest p05 is an internal reference: the same forest supplied the correction. Edge forest also darkened. Non-overlapping 250 m blocks can still be correlated.

The date shuffle holds the spatial footprint fixed and counts how often other assignments of whole images produce darkening at least as strong. Its fraction assumes the acquisition dates are exchangeable. Seasonal weather and irregular sampling weaken that assumption. Site-mean rainfall places the first qualifying rain on 26 October; the 061 response on 28 October and the 125 response on 1 November give one observation per orbit. They do not measure lasting recovery.

For land-area comparisons, use each peat boundary separately and divide by valid area in the same on-peat or off-peat class. The Track 5 dried mask uses the forest p05, not the stronger 1 dB fall. Missing mask coverage stays unknown. The study boxes overlap, so do not add the two areas. For both official-map queries we checked the returned feature IDs, excluded centres outside the requested geographic extent, and treated zero inside as “no mapped polygon.” This does not prove peat is absent. Track 3’s exploratory comparison with the independent CIFOR peat map found boundary agreement close to chance at both sites. The eastern peat-area estimates are particularly sensitive to the choice of map. The verified Track 5 data-v9 handoff covers PEATMAP and the official map. [Track 3 comparison and methods](https://github.com/tommyquak/GarugonsSpaceApps/pull/44)

**HV rebound correction in data-v9.** The original HV rebound rasters included a forest baseline shift of +0.167 dB on track 061 and −0.034 dB on track 125 at both sites. Track 5 held the eight affected medians. On 14 November the team replaced the rasters with HV as measured. We checked the replacement files against the release checksums and reproduced the whole-site and driest-tenth medians for both orbits and sites from the radar stacks. All eight are now final. On west track 061 the whole-site median changed from +0.1282 dB to −0.0388 dB, a small change in echo strength. Each orbit contributes only one observation after the rain. [Correction record](https://github.com/tommyquak/GarugonsSpaceApps/issues/1#issuecomment-6873030852)
