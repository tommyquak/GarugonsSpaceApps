# Recovery after the rain

Track 2b, owner Reagan. What the first rain brought back, in HH and in HV, on the same 250 m blocks and against the same intact-forest baseline as the dry-down in `pipeline/drying/`.

| Script | What it does | Writes |
|---|---|---|
| `recovery.py` | Fall, rebound and what is left, per orbit. Compares the two orbits' rebounds once both exist. | `recovery_<pol>_<site>_<track>.tif` (rebound), `recovery_left_<pol>_<site>_<track>.tif` (what the rain did not bring back), `recovery_*` in `validation.json` |
| `sensitivity.py` | Reruns the recovery with the last dry day one pass earlier, one late pass instead of two, and the second pass after the rain. | `sensitivity_recovery_<site>_<track>.json`, `recovery_*_share_regained_sensitivity_*` in `validation.json` |

Run order, after the dry-down layers and the noise floor exist (`pipeline/run_all.sh` steps 1 to 5):

```
python pipeline/recovery/recovery.py    --site west --track 125 --other-track 061 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
python pipeline/recovery/recovery.py    --site west --track 061 --other-track 125 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
python pipeline/recovery/sensitivity.py --site west --track 125 --other-track 061 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
```

Tests: `python -m pytest pipeline/tests/test_recovery.py`.

## What to know

- "Strongly dried" means the block fell by 1 dB or more in HH on this orbit and on the other one. The other orbit's fall is measured independently, so a rebound that tracks it is not an artefact of this track.
- `--dry-until` is 25 Oct for now. It is replaced by the last dry day from track 3's rainfall record once that exists.
- Not done yet, waiting on track 3: recovery split on mapped peat and off it, and burnt blocks reported apart from blocks that only dried. Burnt land should come back in HH (the ground is wet again) but not in HV (the canopy is gone).
