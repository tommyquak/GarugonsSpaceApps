# Drying (track 2a)

Turns the radar stacks into the dry-down layers. Run from the repo root, in this order:

```
S=pipeline/out/stacks; L=pipeline/out/layers
python pipeline/drying/reference.py  --stacks $S/west_125.npz $S/west_061.npz --out $L
python pipeline/drying/baseline.py   --stack $S/west_125.npz --reference $L/reference_west.tif --out $L
python pipeline/drying/baseline.py   --stack $S/west_061.npz --reference $L/reference_west.tif --out $L
python pipeline/drying/drydown.py    --stack $S/west_125.npz --baseline $L/baseline_125.json --start-from 20260710 --dry-until 20261025 --out $L
#   ... the same for west_061, east_125 and east_061, each with its own track's baseline
python pipeline/drying/noise_floor.py --layers $L --sites west east --tracks 125 061
python pipeline/drying/selfcheck.py   --stacks $S --layers $L --dry-until 20261025
python pipeline/drying/sensitivity.py --stacks $S --layers $L --start-from 20260710 --dry-until 20261025
python pipeline/drying/one_look_map.py --layers $L --stacks $S --sites west east --tracks 125 061 --min-db 1 --out pipeline/out/one_look_map.png
```

## What each step does

| Step | Script | In one line |
|---|---|---|
| 0 | `reference.py` | Draws the intact reference forest once for both orbits: closed forest at least 4 km from any edge. |
| 1 | `baseline.py` | Measures the scene-wide shift of each pass on that forest, so it can be removed. |
| 2 | `drydown.py` | HH late in the dry season minus HH on the rain-free start passes, on 250 m blocks, shift removed. |
| 3 | `noise_floor.py` | The 5th percentile of the score on the reference forest, and which blocks went beyond that on both orbits. |
| 4 | `one_look_map.py` | The map. |
| 5 | `split.py` | Areas on and off mapped peat, near and away from fire. Needs track 3's peat and fire layers. |
| - | `selfcheck.py` | Seven checks for artefacts we could have introduced. |
| - | `sensitivity.py` | How much the result depends on choices we made. |

## What we learned while checking

- **Forest edges dry.** The score falls by about 0.5 dB within 250 m of a forest edge and reaches zero only 4 km inside. The reference is therefore deep forest, and edges are part of the signal.
- **Show the size of the fall, not a yes or no.** In this El Nino year about half of the west box fell beyond the noise floor.
- **HH for the ground.** HV gives a similar map but follows vegetation as well.
- **`--start-from` and `--dry-until`** come from the rainfall record by the rules in `pipeline/season.py`: the start is the first rain-free pass, the end is the last day before the rain returned. The first version started from the first two passes of the record, which came just after rain and overstated the fall by almost half.
- **"Noise floor" in file and key names means the 5th percentile of change in deep forest.** It is not a noise level for open land. See `docs/LIMITS.md`.
