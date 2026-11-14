# How the sources are fused

The app's recommendations come from five independent sources. This file says how they are combined, and why it is done this way. The machine-readable version is `pipeline/fusion/ontology.json`; `pipeline/fusion/blocks.py` reads its thresholds and rules from there, and the app draws its evidence graph from the same file.

## The principle: agreement, not weights

We have no ground measurements for 2026, so there is nothing to fit weights or train a model against. Any score with weights would be invented. What can be defended is agreement between sources that do not share errors:

- two radar orbits that look from opposite sides at different times of day,
- a thermal fire sensor that has nothing to do with the radar,
- a peat map and a canal map made by other people for other purposes.

So every statement about a block needs the sources named in its rule, and confidence is a count of how many independent lines of evidence agree.

## The vocabulary

| Thing | Meaning | Example |
|---|---|---|
| Source | A dataset from one instrument or one mapping effort | NISAR dawn orbit; FIRMS |
| Block | A 1 km square of ground | `west-042-017` |
| Observation | One number about a block from one source | HH fell 2.1 dB on the dawn orbit |
| State | A yes or no statement, decided by a rule over observations | Dried |
| Action | What a restoration team could do, decided by a rule over states | Rewet first |

The chain is always Source, Observation, State, Action, and a block keeps every link, so each recommendation can show the numbers that produced it.

## States

| State | Rule | Why |
|---|---|---|
| On mapped peat | Half or more of the block is peat in PEATMAP | Dry peat is what burns and loses carbon |
| Dried | HH fell 1 dB or more on the dawn orbit and on the dusk orbit | HH carries the ground echo under vegetation and falls as the ground dries; 1 dB is about three times the noise floor |
| Burnt | A quarter or more of the block lies within 200 m of a fire detection | A thermal detection, independent of the radar |
| Did not come back | After the rain, HH is still below the start of the season by more than the noise floor, on both orbits | Wet ground brightens within days; ground that stays dark lost more than surface moisture |
| Canopy not recovering | Burnt, and HV is still 0.5 dB or more down after the rain on both orbits | HV comes from the woody canopy, which rain does not bring back |
| Near a canal | Typical distance to a mapped canal is 1 km or less | Canals are what drain peat |

## Actions

The first rule that holds, from the top:

| Action | Rule | What it means for a team |
|---|---|---|
| Assess the burn | On peat and burnt | Check the ground for lost canopy; plan rewetting and replanting |
| Rewet first | On peat, dried, not burnt, did not come back | A first candidate for canal blocking |
| Watch | On peat, dried, not burnt, came back with the rain | It will dry again next season: a place to patrol |
| No action flagged | Everything else | Steady, or outside mapped peat. Fire outside peat is still shown |

## Confidence

One point when the action's rule holds, plus one for each further condition that also holds:

- Assess the burn: canopy not recovering; fire on three or more days; also dried.
- Rewet first and Watch: near a canal; fell 2 dB or more on both orbits.

Three points or more is high, two is medium, one is low.

## Fire-prone ground: a hindcast, not a forecast

`pipeline/fusion/hindcast.py` asks one question after the fact: part way through the dry season, had the radar already marked the peat that later burned? It uses only radar passes before a cut date (1 August) and only fire from that date on, on peat blocks with no earlier fire.

How to read the result honestly:

- **Across all peat, the difference is large,** but most of it is the difference between intact forest, which neither dries nor burns, and everything else.
- **Inside drained peat only** (within 1 km of a mapped canal) the difference is smaller and is the fairer number to quote. It is in `validation.json` under `hindcast_near_canal_*`.
- **Distance to a canal alone does about as well** at ranking where fire came. The radar's contribution is the condition of the ground this season, updated every 12 days, not a better map of where drainage is.
- **Fires are lit by people.** Dry ground makes fire possible. Say "ready to burn" or "fire-prone this season", never "predicted".

## What this is not

- **Not a measurement of need.** It ranks where to look first. A team on the ground decides.
- **Not complete.** OpenStreetMap misses canals, and the peat map has its own errors.
- **Not tested against the ground.** No field data exists for this season. The checks are internal: the two orbits agree, intact forest is not flagged, and the rules are fixed before the result is seen.
- **Peat only, by choice.** Fire and drying outside mapped peat are real and are shown on the map, but no action is attached to them.
