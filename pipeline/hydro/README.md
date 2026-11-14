# Water-table bridge

There are no water-level measurements for 2026, the year NISAR observed. There are daily records for 2013 to 2018 at two sites near Palangka Raya, about 9 km north of the west box. This folder uses those records to bring a ground measurement into the project in the only way open to us: a small model fitted to the real record, tested on years it did not see, and then driven by 2026 rainfall.

```
python pipeline/hydro/gauges.py --out pipeline/out/hydro
python pipeline/hydro/rain_history.py --out pipeline/out/hydro --spans 2013-01-01:2018-12-31 2026-01-01:2026-11-12
python pipeline/radar/pull_gcov.py --site gauges --out data/gcov/gauges
python pipeline/radar/build_stack.py --src data/gcov/gauges --track 125 --out pipeline/out/stacks/gauges_125.npz
python pipeline/radar/build_stack.py --src data/gcov/gauges --track 61 --out pipeline/out/stacks/gauges_061.npz --like pipeline/out/stacks/gauges_125.npz
python pipeline/hydro/model.py --hydro pipeline/out/hydro --year 2026
python pipeline/hydro/compare.py --hydro pipeline/out/hydro --stacks pipeline/out/stacks --layers pipeline/out/layers
```

Or `WITH_HYDRO=1 SKIP_PULL=1 pipeline/run_all.sh`, which runs the last two once the downloads above are on disk. The rainfall history takes about 40 minutes.

| Script | What it does |
|---|---|
| `gauges.py` | Downloads the published record (Hirano, CC BY 4.0) and writes it as JSON |
| `rain_history.py` | Daily NASA rainfall over the gauge sites, for the gauge years and for 2026 |
| `model.py` | Fits a four-number water-table model per site, tests it by leaving each year out, runs it on 2026 |
| `compare.py` | Sets the radar's HH and HV at each site beside the modelled water table |

## How to read the result

- **The model's skill is the honest part.** On years it was not fitted to, it follows the measured water table with a correlation of 0.74 to 0.94 and an error of 8 to 26 cm, apart from one half-year of record.
- **The 2026 water table is modelled, not measured.** Say so every time it is shown.
- **The comparison with the radar is weak support, not validation.** Both curves answer the same rain, there are only ten or eleven passes, and some passes were taken on rain days. At the drained site HH moves with the modelled water table on the dawn orbit and less clearly at dusk; under the forest with little drainage the radar barely moves, as the physics leads one to expect.
- **A slope in decibels per metre is not a calibration.** It is one site, one season, against a model.

The site coordinates and the one inconsistency we found in their published values are in `sites.json`.
