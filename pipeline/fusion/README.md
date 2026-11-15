# Fusion into blocks and classes

Track 2c, owner Tommy. Turns the layers of the other tracks into one record per 1 km block: what was observed there, which states hold, and the class that follows. The full account, with the thresholds and the reasons for them, is `docs/FUSION.md`; the output format is `docs/DATA_CONTRACT.md` section 6.

| File | What it does | Reads | Writes |
|---|---|---|---|
| `ontology.json` | The vocabulary and the rules: sources, observations, states, classes, each with its threshold. The app reads the same file (`app/public/blocks/ontology.json`) | | |
| `blocks.py` | One record per 1 km block. A state is a fixed rule over observations, and a class is the first rule in the table that a block meets. Nothing is weighted or learned | Radar stacks; the drydown, recovery, fire, peat and canal layers | `blocks_<site>.geojson`, `blocks_<site>.csv`, entries in `validation.json` |
| `hindcast.py` | A test done after the fact: did an early fall in the echo separate peat that later burned from peat that did not? It did not clearly, and the claim was withdrawn (`docs/LIMITS.md`) | The blocks, and the FIRMS detections by date | `hindcast_<site>.json`, entries in `validation.json` |

```
python pipeline/fusion/blocks.py --site west --tracks 125 061 --start-from 20260710 --dry-until 20261025 \
    --stacks pipeline/out/stacks --layers pipeline/out/layers --out pipeline/out/blocks
python pipeline/fusion/hindcast.py --site west --tracks 125 061 --layers pipeline/out/layers \
    --firms data/firms/west --out pipeline/out/blocks
```

`pipeline/run_all.sh` runs both for each site once the fire, peat and canal layers exist. `app/scripts/copy_blocks.py` copies the result into the app.
