# SI use: Gabriel

One line per use, same columns for everyone. Rules in `AGENTS.md` section 6.

| Date (SGT) | Who | SI tool | What it was used for | Files |
|---|---|---|---|---|
| 14 Nov | Gabriel | Coding assistant | Fire date window: fire layers that stop at the last dry day, their tests and contract line | `pipeline/context/fire_layers.py`, `pipeline/context/README.md`, `pipeline/tests/test_fire_layers.py`, `pipeline/run_all.sh`, `docs/DATA_CONTRACT.md` |
| 14 Nov | Gabriel | Coding assistant | CIFOR peat map as an independent check of the PEATMAP boundary, its tests, and the run_all, requirements and contract lines | `pipeline/context/peat_cifor.py`, `pipeline/context/README.md`, `pipeline/tests/test_peat_cifor.py`, `pipeline/run_all.sh`, `requirements.txt`, `docs/DATA_CONTRACT.md` |
| 14 Nov | Gabriel | Coding assistant | Repeat fire: 2026 fire against the 2015, 2019 and 2023 seasons, its tests, and the run_all and contract lines | `pipeline/context/repeat_fire.py`, `pipeline/context/fire_layers.py`, `pipeline/context/README.md`, `pipeline/tests/test_repeat_fire.py`, `pipeline/run_all.sh`, `docs/DATA_CONTRACT.md` |
