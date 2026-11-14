# How the sources are fused

The app groups every 1 km block into a screening class. This file says how, and what a class does and does not mean. The machine-readable version is `pipeline/fusion/ontology.json`; `pipeline/fusion/blocks.py` reads its thresholds and rules from there, and the app draws its evidence graph from the same file.

This is version 2. The first version called its classes "rewet first", "watch" and "assess the burn" and graded them by "confidence". An independent audit showed those names claimed more than the data supports (`docs/AUDIT.md`). The classes now say what was seen.

## The principle: fixed rules, no weights

We have no ground measurements for 2026, so there is nothing to fit weights or train a model against. Any weighted score would be invented. Each statement about a block is therefore a fixed rule over named observations, and each block keeps the numbers that decided it.

The sources are of four kinds: the radar (two orbits of one instrument, which share its calibration and our baseline), a thermal fire sensor, a peat map and a canal map. The two radar orbits agreeing shows that a change is on the ground and not in one orbit. It does not show what the change is.

## The vocabulary

| Thing | Meaning | Example |
|---|---|---|
| Source | A dataset from one instrument or one mapping effort | NISAR dawn orbit; FIRMS |
| Block | A 1 km square of ground | `west-042-017` |
| Observation | One number about a block from one source | HH fell 2.1 dB on the dawn orbit |
| State | A yes or no statement, decided by a rule over observations | HH fell on both orbits |
| Class | What was seen, and what a field team could check. Stored as `action` in the data | Fell, and still low after the rain |

The chain is always source, observation, state, class, and a block keeps every link.

## States

| State | Rule | What it does and does not mean |
|---|---|---|
| On mapped peat | Half or more of the block is peat in PEATMAP | Classes are given on mapped peat only |
| HH fell on both orbits | HH fell 1 dB or more from the dry start to the late dry season, on the dawn orbit and on the dusk orbit | Over open land HH falls as the surface dries; it also changes with clearing, harvest and standing water |
| Fire detected | A quarter or more of the block lies inside the footprint of a fire detection | Active fire seen from space, not burnt area; some fire is missed |
| Still low after the first rain | HH still 0.5 dB or more below the dry start on the first pass after the rain, on both orbits | One pass per orbit within days of heavy rain; unexplained |
| HV low after the rain | Fire detected, and HV still 0.5 dB or more below the dry start on both orbits, HV as measured | HV comes mostly from woody vegetation |
| Fire on several days | Detections on three or more days at one spot | Not a single false detection |
| No fire detected within 1 km | Nothing detected within 1 km of any part of the block | The cautious reading of "no fire nearby" |
| Near a mapped canal | Typical distance to a mapped canal is 1 km or less | Context only, used in no class |

The start of the dry season and its end are read from the rainfall record by the rules in `pipeline/season.py`, so the fall is not measured from a rain-wet surface.

## Classes

The first rule that holds, from the top:

| Class | Rule | What a field team could check |
|---|---|---|
| Fire detected on peat | On peat, fire detected | Burn damage and lost vegetation |
| Fell, and still low after the rain | On peat, HH fell on both orbits, no fire detected, still low after the rain | Why it stayed low. We do not know |
| Fell, and came back with the rain | On peat, HH fell on both orbits, no fire detected, back near the dry start after the rain | Nothing specific |
| No class | Everything else | Fire outside peat is still shown on the map |

## Agreement

A count, not a probability. One point when the class's rule holds, plus one for each further condition that also holds:

- Fire detected on peat: fire on several days; HV low after the rain.
- The two "fell" classes: no fire detected within 1 km.

Three points is high, two is medium, one is low.

## At a glance: three levels

The "Where to check" view opens coloured by level, for a first look. The levels are a grouping of the classes and states above, made in the app (`app/src/actions/levels.ts`). They add no threshold and no number.

| Level | Blocks in it |
|---|---|
| Most affected | Fire detected with agreement high: fire on several days, and HV still low after the rain |
| Affected | Fell, and still low after the rain; or fire detected with HV still low after the rain |
| Changed, then recovered | Every other classed block: fire, or a fall, with no lasting change seen after the rain |

The order is by signs of lasting change, not by harm. Nothing here was checked on the ground, and the size of the fall plays no part: land beside a canal can fall a long way and recover with the first rain.

## The fire-prone test

`pipeline/fusion/hindcast.py` asks, after the fact, whether an early fall marked the peat that later burned, using only radar before 1 September and only fire from then on. Across all peat in the west box the difference is large, and it is forest against open land. Inside drained land it is not distinguishable from zero in either box. We make no claim about fire-prone ground; the numbers and their ranges are in `validation.json` under `hindcast_*` and in `docs/LIMITS.md`.

## What this is not

- **Not a recommendation.** No class says to block a canal or to intervene.
- **Not a measurement of need or of water.** It shows where the radar echo changed and where fire was detected.
- **Not tested against the ground.** No field data exists for this season.
- **Not complete.** OpenStreetMap misses canals, and the peat map has its own errors.
- **Peat only, by choice.** Fire and change outside mapped peat are real and are shown on the map, but no class is attached to them.

The thresholds were written on 14 Nov 2026, the day of the first results, and have not been tuned since. What moves when they move is in `docs/LIMITS.md` and `pipeline/out/layers/sensitivity.json`.
