# Pipeline

Python that turns NISAR files into map layers and `out/validation.json`. Formats are in `docs/DATA_CONTRACT.md`.

| Folder | Track | Owner |
|---|---|---|
| `radar/` | 1. Radar data and stacks | Tommy |
| `drying/` | 2a. The fall: baseline, dry-down, forest spread | Tommy |
| `recovery/` | 2b. Recovery after the rain | Reagan |
| `context/` | 3. Fire and context layers | Gabriel |
| `fusion/` | 2c. Fusion into 1 km blocks and classes | Tommy |
| `hydro/` | Rainfall-driven water-table model beside the radar | Tommy |
| `checks/` | 5. Checks and limits | Anson |

Beside the folders:

| File | What it is |
|---|---|
| `run_all.sh` | Rebuilds every output in order; its opening comment lists the options |
| `season.py` | The dry season read from the rainfall record: which passes are its start and where it ends |
| `vjson.py` | Reads and writes `out/validation.json`, the one file every reported number comes from |
| `figures.py` | The figures for the slides, drawn from the outputs |
| `tests/` | Tests of the processing code, on small made-up arrays; they need no data |

Each folder has a README that names its scripts. How the layers are fused into blocks and classes is in `docs/FUSION.md`.

- Each script runs from the repo root, takes its input and output paths as arguments, and has no absolute paths.
- Outputs go to `pipeline/out/`, which is not committed.
- Every script an agent wrote starts with the comment `Written with Super Intelligence (SI) assistance`.
