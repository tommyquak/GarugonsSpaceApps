# Pipeline

Python that turns NISAR files into map layers and `out/validation.json`. Formats are in `docs/DATA_CONTRACT.md`.

| Folder | Track | Owner |
|---|---|---|
| `radar/` | 1. Radar data and stacks | Tommy |
| `drying/` | 2a. Drying: baseline, dry-down, noise floor | Tommy |
| `recovery/` | 2b. Recovery after the rain | Reagan |
| `context/` | 3. Fire and context layers | Gabriel |
| `checks/` | 5. Checks and limits | Anson |

- Each script runs from the repo root, takes its input and output paths as arguments, and has no absolute paths.
- Outputs go to `pipeline/out/`, which is not committed.
- Every script an agent wrote starts with the comment `Written with Super Intelligence (SI) assistance`.
