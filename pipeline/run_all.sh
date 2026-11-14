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
# The pull needs a NASA Earthdata login in ~/.netrc and takes a few hours.
# Everything after the stacks takes a few minutes.
set -euo pipefail

PY=${PYTHON:-python3}
DRY_UNTIL=${DRY_UNTIL:-20261025}   # last day before the rain returned, from the rainfall record
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

echo "== 5. noise floor and the dried layers"
rm -f pipeline/out/validation.json
$PY pipeline/drying/noise_floor.py --layers "$L" --sites $SITES --tracks $ASC $DESC

echo "== 6. recovery after the rain"
for site in $SITES; do
  $PY pipeline/recovery/recovery.py --site "$site" --track $ASC --other-track $DESC --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
done

echo "== 7. checks"
$PY pipeline/drying/selfcheck.py --stacks "$S" --layers "$L" --dry-until "$DRY_UNTIL" > "$L/selfcheck_report.json"
$PY pipeline/drying/sensitivity.py --stacks "$S" --layers "$L" --dry-until "$DRY_UNTIL"

echo "== 8. time series for the app, and the map"
for site in $SITES; do
  $PY pipeline/drying/series.py --site "$site" --tracks $ASC $DESC --stacks "$S" --layers "$L" --out pipeline/out/series
done
$PY pipeline/drying/one_look_map.py --layers "$L" --stacks "$S" --sites $SITES --tracks $ASC $DESC --min-db 1 --out pipeline/out/one_look_map.png > /dev/null

echo "done: layers in $L, numbers in pipeline/out/validation.json"
