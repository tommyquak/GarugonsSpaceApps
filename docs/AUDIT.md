# Independent audit and our response

On 14 Nov 2026, part way through the build, we asked an independent reviewer (a Super Intelligence agent given the code and outputs, told to be adversarial and to recompute the numbers itself) to audit the project for scientific rigour. It reproduced our block counts, fire layer and fire comparison exactly, confirmed the radar signal, and found that several of our interpretations did not hold. This file lists what it found and what we changed. The limits that remain are in `docs/LIMITS.md`.

## What it confirmed

- The two orbits agree on where HH fell: r about 0.9 overall, and 0.85 to 0.95 inside single land-cover classes, so the agreement is not just forest against open land.
- Deep forest is a stable yardstick in the dry season, and the reference is not selected on its own stability.
- The fall at forest edges is not an artefact of block averaging.
- The two orbits are registered to each other within about 12 m.
- The code reruns and reproduces every reported number.

## What it found, and what we did

| # | Finding | Severity | Our response |
|---|---|---|---|
| 1 | The start passes came just after rain, so much of the "drying" was the surface losing that wetness | Critical | Fixed. The start passes are now chosen from the rainfall record by a rule (`pipeline/season.py`). Western peat that fell 1 dB or more went from 1,349 to 755 km2. Both are in `sensitivity.json` |
| 2 | "Rewet first" was not defensible: it rested on one pass per orbit taken just after rain, and picked blocks farther from canals and woodier than the rest | Critical | Withdrawn. The class is now "fell, and still low after the rain", says what was seen, and recommends nothing beyond a field check |
| 3 | The passes after the rain come from a later NASA processing release than the dry passes | Critical | Not fixable this weekend. Stated in the limits, with the uncertainty it adds to the size of the rise (0.3 to 0.4 dB) |
| 4 | The fire-prone comparison was not distinguishable from no effect inside drained land | Major | Rerun from the dry start with 95% ranges from 10 km tiles. Inside drained land the difference is 3 points (range minus 9 to plus 18). We withdrew the claim |
| 5 | Shifting HV by the forest baseline created about 0.5 dB of apparent HV loss | Major | Fixed in the fusion: HV is used as measured. We now claim only the contrast between peat with and without fire detections |
| 6 | The 200 m fire buffer was smaller than the sensors' pixels | Major | Fixed. Each detection is buffered by its own pixel size, and a second layer marks everything within 1 km. Fire on western peat went from 29% to 37% |
| 7 | "Noise floor" and "false-alarm rate" were partly true by construction | Major | Reworded as "the 5th percentile of change in deep forest". The limits say what it means for open land |
| 8 | Thresholds had no source, and we wrote that the rules were fixed before the result was seen | Major | The sentence was wrong and is deleted. The thresholds are stated as choices made the same day, with their sensitivity |
| 9 | The forest offset is applied far from where it is measured | Major | Stated in the limits. Not fixed |
| 10 | The fusion was close to a land-cover and fire map with action words on it | Major | Classes renamed to what was seen. "Confidence" is now "agreement", a count. Canal distance is context only. The limits say most classed blocks use no radar |
| 11 | The limits and references files were empty | Major | `docs/LIMITS.md` is written from this audit. References are with track 5 |
| 12 | "Nobody can watch the drying happen" overclaimed | Major | Reworded. Other satellites observe surface moisture over these peatlands |
| 13 | The two peat maps are the same mapping | Minor | Reworded: not an independent check |
| 14 | Gaps of 24 and 36 days in the record | Minor | In the limits |
| 15 | Burnt open peat fell less in HH than unburnt | Minor | In the limits |
| 16 | The recovery sensitivity and placebo show timing only | Minor | In the limits |
| 17 | Tests cover arithmetic, not the science | Minor | Open. More tests are on the list |
| 18 | Smaller data-quality notes | Minor | In the limits |

## What we can still claim

1. Between mid July and mid October 2026, L-band HH fell by 1 dB or more, relative to deep forest, on about 755 km2 of mapped peat in the west box and 292 km2 in the east, and two orbits that look from opposite sides agree on where (r about 0.9).
2. Deep intact forest is a stable yardstick in the dry season.
3. Within days of the first heavy rain, HH on that land rose by about 1 dB on both orbits, and not one pass earlier.
4. Fire was detected on 37% of mapped peat in the west box and 61% in the east. Among western peat blocks where HH fell by 1 dB or more on both orbits, the median HV change from the dry-season start to the first dawn pass after rain was 0.54 dB lower for blocks with fire detections. The other three comparisons remain exploratory: the differences were 0.34 dB at western dusk, 0.40 dB at eastern dawn and 0.29 dB at eastern dusk, all lower in the fire-detection group. The groups use detections from the full study period, including dates after the radar pass.
5. Every number comes from open data and open code that reruns from the published stacks.

## What we no longer claim

- That the map shows where peat "dried" in the sense of a lower water table.
- That any block is a candidate for canal blocking.
- That an early fall marks fire-prone ground.
- That HH and HV are separate "water" and "vegetation" channels.
