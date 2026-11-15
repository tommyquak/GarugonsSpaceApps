# Tests

Tests of the processing code. They build small arrays in memory, so they need no data and no network, and run in a few seconds.

```
python -m pytest pipeline/tests pipeline/checks
```

| File | What it tests |
|---|---|
| `test_radar.py` | Averaging to 50 m in power, reading a granule's name, and regridding between grids (`pipeline/radar/`) |
| `test_drying.py`, `test_by_cover.py` | The reference forest, the scene-wide shift, the fall and the split by cover (`pipeline/drying/`) |
| `test_recovery.py` | The change on the first pass after the rain (`pipeline/recovery/`) |
| `test_fire_layers.py`, `test_repeat_fire.py`, `test_burn_flag.py`, `test_peat_cifor.py` | The fire, coherence and peat layers (`pipeline/context/`) |
| `conftest.py` | Puts the repository root on the import path |

The tests of the independent checks are beside them, in `pipeline/checks/test_*.py`. Both folders run on every pull request (`.github/workflows/tests.yml`).
