#!/usr/bin/env bash
# Written with Super Intelligence (SI) assistance.
#
# Rebuild every pipeline output, from NASA's archive to the numbers in validation.json.
# Run from the repo root.
#
#   pipeline/run_all.sh                 pull the NISAR windows, build the stacks, then everything else
#   SKIP_PULL=1 pipeline/run_all.sh     start from stacks already in pipeline/out/stacks
#                                       (for example downloaded from the data-v1 release)
#
#   WITH_CONTEXT=1 ...                  also rebuild the fire, rain, peat and canal layers (track 3).
#                                       Needs FIRMS_MAP_KEY in the environment and an Earthdata login.
#                                       Without it, layers already in pipeline/out/layers are used.
#
# The pull needs a NASA Earthdata login in ~/.netrc and takes a few hours.
# Everything after the stacks takes a few minutes.
set -euo pipefail

PY=${PYTHON:-python3}
DRY_UNTIL=${DRY_UNTIL:-20261025}   # last day before the rain returned: last_dry_day_<site> in validation.json
SEASON_START=${SEASON_START:-2026-05-01}
SEASON_END=${SEASON_END:-2026-11-12}
S=pipeline/out/stacks
L=pipeline/out/layers
SITES="west east"
ASC=125    # ascending track, dawn pass
DESC=061   # descending track, dusk pass

if [ -z "${SKIP_PULL:-}" ]; then
  echo "== 1. pull NISAR L2 GCOV windows"
  for site in $SITES; do
    $PY pipeline/radar/pull_gcov.py --site "$site" --out "data/gcov/$site"
  done
  echo "== 2. build the radar stacks"
  for site in $SITES; do
    $PY pipeline/radar/build_stack.py --src "data/gcov/$site" --track $ASC --out "$S/${site}_$ASC.npz"
    $PY pipeline/radar/build_stack.py --src "data/gcov/$site" --track $DESC --out "$S/${site}_$DESC.npz" --like "$S/${site}_$ASC.npz"
  done
fi

echo "== 3. reference forest and baseline"
$PY pipeline/drying/reference.py --stacks "$S/west_$ASC.npz" "$S/west_$DESC.npz" --out "$L"
for track in $ASC $DESC; do
  $PY pipeline/drying/baseline.py --stack "$S/west_$track.npz" --reference "$L/reference_west.tif" --out "$L" > /dev/null
done

echo "== 4. dry-down, per-pass layers"
for site in $SITES; do
  for track in $ASC $DESC; do
    $PY pipeline/drying/drydown.py --stack "$S/${site}_$track.npz" --baseline "$L/baseline_$track.json" --dry-until "$DRY_UNTIL" --out "$L"
    $PY pipeline/drying/per_pass.py --stack "$S/${site}_$track.npz" --baseline "$L/baseline_$track.json" --out "$L"
  done
done

echo "== 4b. time series for the app"
for site in $SITES; do
  $PY pipeline/drying/series.py --site "$site" --tracks $ASC $DESC --stacks "$S" --layers "$L" --out pipeline/out/series
done

echo "== 5. noise floor and the dried layers"
rm -f pipeline/out/validation.json
$PY pipeline/drying/noise_floor.py --layers "$L" --sites $SITES --tracks $ASC $DESC

if [ -n "${WITH_CONTEXT:-}" ]; then
  echo "== 5b. context layers: fire, rain, peat, canals"
  for site in $SITES; do
    $PY pipeline/context/pull_firms.py --site "$site" --start "$SEASON_START" --out "data/firms/$site"
    $PY pipeline/context/peatmap.py --site "$site" --layers "$L"
    $PY pipeline/context/peat.py --site "$site" --layers "$L"      # official map, local cross-check only
    $PY pipeline/context/canals.py --site "$site" --layers "$L"
  done
fi
for site in $SITES; do   # these two only read what is on disk, so they always run when their input exists
  if [ -d "data/firms/$site" ]; then
    $PY pipeline/context/fire_layers.py --site "$site" --firms "data/firms/$site" --layers "$L" --series pipeline/out/series
  fi
  if [ -n "${WITH_CONTEXT:-}" ] || [ -f "$L/rain_daily_$site.json" ]; then
    $PY pipeline/context/rain.py --site "$site" --start "$SEASON_START" --end "$SEASON_END" --out "$L"
  fi
done

echo "== 6. recovery after the rain"
for site in $SITES; do
  $PY pipeline/recovery/recovery.py --site "$site" --track $ASC --other-track $DESC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/recovery.py --site "$site" --track $DESC --other-track $ASC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/sensitivity.py --site "$site" --track $ASC --other-track $DESC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/sensitivity.py --site "$site" --track $DESC --other-track $ASC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
done

echo "== 6b. split by peat and fire (skips a site until track 3's layers are in $L)"
$PY pipeline/drying/split.py --layers "$L" --sites $SITES --tracks $ASC $DESC

echo "== 6c. fusion: one record per 1 km block (skips a site until the fire, peat and canal layers exist)"
for site in $SITES; do
  if [ -f "$L/fire_days_$site.tif" ] && [ -f "$L/peat_peatmap_$site.tif" ] && [ -f "$L/canal_distance_$site.tif" ]; then
    $PY pipeline/fusion/blocks.py --site "$site" --tracks $ASC $DESC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L" --out pipeline/out/blocks
  fi
done

echo "== 7. checks"
$PY pipeline/drying/selfcheck.py --stacks "$S" --layers "$L" --dry-until "$DRY_UNTIL" > "$L/selfcheck_report.json"
$PY pipeline/drying/sensitivity.py --stacks "$S" --layers "$L" --dry-until "$DRY_UNTIL"

echo "== 8. the map"
$PY pipeline/drying/one_look_map.py --layers "$L" --stacks "$S" --sites $SITES --tracks $ASC $DESC --min-db 1 --out pipeline/out/one_look_map.png > /dev/null

echo "done: layers in $L, numbers in pipeline/out/validation.json"
