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
#   WITH_HYDRO=1 ...                    also run the water-table bridge (pipeline/hydro/README.md)
#   WITH_CONTEXT=1 ...                  also rebuild the fire, rain, peat and canal layers (track 3).
#                                       Needs FIRMS_MAP_KEY in the environment and an Earthdata login.
#                                       Without it, layers already in pipeline/out/layers are used.
#
# The pull needs a NASA Earthdata login in ~/.netrc and takes a few hours.
# Everything after the stacks takes a few minutes.
set -euo pipefail

PY=${PYTHON:-python3}
# The start and the end of the dry season come from the rainfall record (pipeline/season.py) when
# it is on disk. These two values are the fallback for a first run with no rainfall file yet.
START_FROM=${START_FROM:-20260710}
DRY_UNTIL=${DRY_UNTIL:-20261025}
SEASON_START=${SEASON_START:-2026-05-01}
SEASON_END=${SEASON_END:-2026-11-12}
FIRE_YEARS=${FIRE_YEARS:-"2015 2019 2023"}   # earlier fire seasons for repeat fire (July to November of each)
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

if [ -f "$L/rain_daily_west.json" ]; then
  eval "$($PY pipeline/season.py --rain "$L/rain_daily_west.json" | tail -1)"
  echo "== dry season from the rainfall record: start passes from $START_FROM, last dry day $DRY_UNTIL"
fi

echo "== 3. reference forest and baseline"
$PY pipeline/drying/reference.py --stacks "$S/west_$ASC.npz" "$S/west_$DESC.npz" --out "$L"
for track in $ASC $DESC; do
  $PY pipeline/drying/baseline.py --stack "$S/west_$track.npz" --reference "$L/reference_west.tif" --out "$L" > /dev/null
done

echo "== 4. dry-down, per-pass layers"
for site in $SITES; do
  for track in $ASC $DESC; do
    $PY pipeline/drying/drydown.py --stack "$S/${site}_$track.npz" --baseline "$L/baseline_$track.json" --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --out "$L"
    $PY pipeline/drying/per_pass.py --stack "$S/${site}_$track.npz" --baseline "$L/baseline_$track.json" --start-from "$START_FROM" --out "$L"
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
    for y in $FIRE_YEARS; do   # past seasons do not change, so each is pulled once
      [ -d "data/firms_history/$site/$y" ] || $PY pipeline/context/pull_firms.py --site "$site" --start "$y-07-01" --end "$y-11-30" --out "data/firms_history/$site/$y"
    done
    $PY pipeline/context/peatmap.py --site "$site" --layers "$L"
    $PY pipeline/context/peat.py --site "$site" --layers "$L"      # official map, local cross-check only
    $PY pipeline/context/canals.py --site "$site" --layers "$L"
  done
fi
for site in $SITES; do   # these two only read what is on disk, so they always run when their input exists
  if [ -d "data/firms/$site" ]; then
    $PY pipeline/context/fire_layers.py --site "$site" --firms "data/firms/$site" --layers "$L" --series pipeline/out/series --dry-until "$DRY_UNTIL"
  fi
  if [ -n "${WITH_CONTEXT:-}" ] || [ -f "$L/rain_daily_$site.json" ]; then
    $PY pipeline/context/rain.py --site "$site" --start "$SEASON_START" --end "$SEASON_END" --out "$L"
    $PY pipeline/season.py --rain "$L/rain_daily_$site.json" > /dev/null     # writes the season dates to validation.json
  fi
  if [ -n "${WITH_CONTEXT:-}" ] || [ -f "data/cifor/TROP-SUBTROP_PeatV21_2016_CIFOR.tif" ]; then
    $PY pipeline/context/peat_cifor.py --site "$site" --layers "$L"     # an independent peat map, local cross-check only
  fi
  if [ -d "data/firms_history/$site" ] && [ -f "$L/fire_days_$site.tif" ] && [ -f "$L/peat_peatmap_$site.tif" ]; then
    $PY pipeline/context/repeat_fire.py --site "$site" --history "data/firms_history/$site" --layers "$L"
  fi
done

echo "== 6. recovery after the rain"
for site in $SITES; do
  $PY pipeline/recovery/recovery.py --site "$site" --track $ASC --other-track $DESC --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/recovery.py --site "$site" --track $DESC --other-track $ASC --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/sensitivity.py --site "$site" --track $ASC --other-track $DESC --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
  $PY pipeline/recovery/sensitivity.py --site "$site" --track $DESC --other-track $ASC --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L"
done

echo "== 6b. split by peat and fire (skips a site until track 3's layers are in $L)"
$PY pipeline/drying/split.py --layers "$L" --sites $SITES --tracks $ASC $DESC
$PY pipeline/drying/by_cover.py --stacks "$S" --layers "$L" --sites $SITES --tracks $ASC $DESC --start-from "$START_FROM"

echo "== 6c. fusion: one record per 1 km block (skips a site until the fire, peat and canal layers exist)"
for site in $SITES; do
  if [ -f "$L/fire_days_$site.tif" ] && [ -f "$L/peat_peatmap_$site.tif" ] && [ -f "$L/canal_distance_$site.tif" ]; then
    $PY pipeline/fusion/blocks.py --site "$site" --tracks $ASC $DESC --start-from "$START_FROM" --dry-until "$DRY_UNTIL" --stacks "$S" --layers "$L" --out pipeline/out/blocks
    if [ -d "data/firms/$site" ]; then
      $PY pipeline/fusion/hindcast.py --site "$site" --tracks $ASC $DESC --layers "$L" --firms "data/firms/$site" --out pipeline/out/blocks
    fi
  fi
done

if [ -n "${WITH_HYDRO:-}" ]; then
  echo "== 6d. water-table bridge (needs the downloads listed in pipeline/hydro/README.md)"
  $PY pipeline/hydro/model.py --hydro pipeline/out/hydro --year 2026
  $PY pipeline/hydro/compare.py --hydro pipeline/out/hydro --stacks "$S" --layers "$L"
fi

echo "== 7. checks"
$PY pipeline/drying/selfcheck.py --stacks "$S" --layers "$L" --dry-until "$DRY_UNTIL" > "$L/selfcheck_report.json"
$PY pipeline/drying/sensitivity.py --stacks "$S" --layers "$L" --start-from "$START_FROM" --dry-until "$DRY_UNTIL"

# Independent Track 5 checks. Write the results only when both calculations agree.
$PY -m pipeline.checks.run --repeat

echo "== 8. the map"
$PY pipeline/drying/one_look_map.py --layers "$L" --stacks "$S" --sites $SITES --tracks $ASC $DESC --min-db 1 --out pipeline/out/one_look_map.png > /dev/null

echo "done: layers in $L, numbers in pipeline/out/validation.json"
