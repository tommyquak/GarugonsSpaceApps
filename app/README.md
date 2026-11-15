# App

The web map: Vite, TypeScript and MapLibre GL JS. A static site with no server, published on GitHub Pages at https://tommyquak.github.io/GarugonsSpaceApps/. Track 4, owners Kalent and Jan Hoe.

## Run it

Node 22.

```
cd app
npm ci
npm run dev        # http://localhost:5173/GarugonsSpaceApps/
npm run build      # type-check (tsc), then build to app/dist
npm run preview    # serve app/dist, to try the built site
```

The site lives under the path `/GarugonsSpaceApps/` (`vite.config.ts`). Every push to `main` builds and publishes it (`.github/workflows/pages.yml`), and every pull request builds it as a check (`.github/workflows/tests.yml`).

## What it reads

Everything is a static file under `public/`, committed, so the app runs without the pipeline.

| Folder or file | What it holds | Made by |
|---|---|---|
| `public/layers/` | `layers.json` and the image of each map layer (`docs/DATA_CONTRACT.md` section 5) | `scripts/make_layers.py` |
| `public/series/` | HH and HV of every pass, packed for the click-a-place chart (section 4) | `pipeline/drying/series.py` |
| `public/season/` | The measured curves of the season view | `scripts/make_season_data.py` |
| `public/blocks/` | The 1 km blocks with their classes, and `ontology.json` (section 6) | `scripts/copy_blocks.py` |
| `public/story/` | Pictures, credits and narration of the opening story | `scripts/make_story_images.py`, `make_story_voice.py` |
| `public/validation.json` | Every reported number, with its status | `pipeline/` and `pipeline/checks/` |
| `public/field-assessment/` | The printable field assessment, one HTML page | written by hand |

Each script says how to run it in its opening comment.

## Where things are in `src/`

| File or folder | What it is |
|---|---|
| `main.ts` | The entry point: builds the map, the header and the panels, and keeps the address bar in step |
| `opening.ts`, `intro/` | The opening story and the entry room |
| `season.ts`, `measure.ts` | The season slider and its "how it was measured" panel |
| `chart/` | The place card and its chart |
| `actions/` | "Where to check": the 1 km blocks by level or class, flat or in 3D, the ranked list and the exports |
| `ontology/` | "How it decides": the rule graph and the card of one block |
| `overlays.ts`, `basemaps.ts`, `maplegend.ts` | Map layers, base maps and the legend |
| `docs.ts`, `markdown.ts` | The Limits and About panels, read from `docs/LIMITS.md` and the top-level `README.md` |
| `link.ts`, `view.ts` | The state kept in the address, so a view can be shared |

The design rules are in `docs/DESIGN.md`.
