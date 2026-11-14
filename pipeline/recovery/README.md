# Recovery after the rain

Track 2b, owner Reagan. What the first rain brought back, in HH and in HV, on the same 250 m blocks and against the same intact-forest baseline as the dry-down in `pipeline/drying/`.

| Script | What it does | Writes |
|---|---|---|
| `recovery.py` | Fall, rebound and what is left, per orbit. Compares the two orbits' rebounds once both exist. | `recovery_<pol>_<site>_<track>.tif` (rebound), `recovery_left_<pol>_<site>_<track>.tif` (what the rain did not bring back), `recovery_*` in `validation.json` |
| `sensitivity.py` | Reruns the recovery with one late pass instead of two, the late pair one pass earlier, and the second pass after the rain. Also a placebo: the rain pretended one pass sooner, which should show no rebound. | `sensitivity_recovery_<site>_<track>.json`, `recovery_*_share_regained_sensitivity_*` and `recovery_*_share_regained_placebo_*` in `validation.json` |

Run order, after the dry-down layers and the noise floor exist (`pipeline/run_all.sh` steps 1 to 5):

```
python pipeline/recovery/recovery.py    --site west --track 125 --other-track 061 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
python pipeline/recovery/recovery.py    --site west --track 061 --other-track 125 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
python pipeline/recovery/sensitivity.py --site west --track 125 --other-track 061 --dry-until 20261025 --stacks pipeline/out/stacks --layers pipeline/out/layers
```

Tests: `python -m pytest pipeline/tests/test_recovery.py`.

## What to know

- "Strongly dried" means the block fell by 1 dB or more in HH on this orbit and on the other one. The other orbit's fall is measured independently, so a rebound that tracks it is not an artefact of this track.
- `--dry-until` is 25 Oct, the last dry day read from the rainfall record (`last_dry_day_<site>` in `validation.json`).
- Once `peat_peatmap_<site>.tif` and `fire_days_<site>.tif` are in the layers folder, every number is also reported in four groups: on or off mapped peat, and burnt (a 2026 fire detection within 200 m) or only dried. Keys `recovery_<pol>_share_regained_<zone>_<site>_<track>`, `recovery_<pol>_median_left_<zone>_<site>_<track>` and `recovery_blocks_<zone>_<site>_<track>`, with zone `on_peat_no_fire`, `on_peat_fire`, `off_peat_no_fire` or `off_peat_fire`. A group with fewer than 100 strongly dried blocks is counted but not summarised.
- HV is used as measured, not shifted by the forest baseline (`docs/AUDIT.md` finding 5). So HV medians and HV shares of the fall carry the scene-wide calibration of each pass and are not to be quoted on their own. The HV number to quote is the contrast between two groups in the same scene, where that calibration cancels: `recovery_hv_left_fire_minus_no_fire_on_peat_<site>_<track>`, HV after the rain on peat with fire detections minus peat without. On `data-v9` (exploratory) it is negative on all four site and orbit pairs, about -0.3 to -0.5 dB.
- Also from the audit: the passes after the rain come from a later NASA processing release than the dry passes, which leaves the size of the HH rise uncertain by 0.3 to 0.4 dB (finding 3).
- Fire detections count the whole of 2026 to date, so a few may come after the pass after the rain.
