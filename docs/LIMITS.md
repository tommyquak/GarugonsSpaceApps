# Limits

What this project can and cannot say. The app shows this file in its Limits panel. It was first written from the findings of an independent audit on 14 Nov 2026 (`docs/AUDIT.md`). Track 5 owns it from here.

## What the map shows, exactly

The colour is how far the L-band HH radar echo fell between a dry start in mid July and mid October 2026, relative to deep intact forest, on 250 m blocks, where two orbits both saw it. It is a change in a radar signal. It is not a measurement of soil moisture or of the water table.

## Limits of the measurement

- **No ground truth.** Nothing here was checked against the ground. No water-level or soil-moisture measurements for 2026 were used, and we found none in public.
- **A fall in HH is not only drying.** Over open and thinly vegetated land HH falls as the surface dries. It also changes with clearing, harvest, standing water and fire, and under dense forest the ground contributes little. The pipeline separates fire detections and nothing else.
- **Forest is zero by definition.** Each pass is shifted so that deep forest does not change. Drying under the forest itself cannot be seen.
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
- **One peat map.** PEATMAP and the official map are the same national mapping, so their 98 to 99% agreement is not an independent check.

## Fire-prone ground: no clear result

We tested whether an early fall marked the peat that later burned. Across all western peat, blocks that had fallen by 0.5 dB by the end of August burned later more often (56% against 29%). Inside drained land the difference vanishes: 3 points in the west (95% range minus 9 to plus 18) and minus 9 points in the east (minus 28 to plus 8). The all-peat gap is forest against open land. We make no claim about fire-prone ground.

## What would test it

- **Water table:** dipwells read on the day of each pass through one dry season, at 40 to 60 blocks spread over the classes and land covers.
- **Surface moisture:** satellite soil moisture products for the same weeks, and a second radar at another wavelength.
- **Fire:** post-season burn scars from optical imagery.
- **Everything:** a second season and a second site.
