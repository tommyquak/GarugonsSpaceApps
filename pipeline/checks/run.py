# Written with Super Intelligence (SI) assistance.
"""Run the independent Track 5 checks and merge their numbers into validation.json."""
import argparse
import fcntl
import json
import math
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import rasterio

from pipeline import vjson
from pipeline.checks import date_shuffle, forest, peat_split, recovery, two_orbit

CHECKS = ("orbit", "forest", "shuffle", "recovery", "peat")
FOREST_KEYS = {"forest_p05": "noise_floor_hh", "forest_p50": "reference_drydown_median",
               "forest_p95": "reference_drydown_p95"}


def released_onset(layers, site, upstream):
    """Confirm Track 3's dated handoff against consecutive daily rainfall totals."""
    row = upstream.get(f"last_dry_day_{site}", {})
    source = row.get("made_by")
    path = layers / f"rain_daily_{site}.json"
    if source not in ("pipeline/season.py", "pipeline/context/rain.py") or not path.is_file():
        return None
    daily = json.loads(path.read_text())
    days = sorted(date.fromisoformat(d) for d in daily)
    if len(days) < 60 or (days[-1] - days[0]).days + 1 != len(days):
        raise ValueError(f"{site}: incomplete daily rainfall record")
    mm = [daily[d.isoformat()] for d in days]
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in mm):
        raise ValueError(f"{site}: invalid daily rainfall total")
    first = min(range(len(mm) - 29), key=lambda i: sum(mm[i:i + 30])) + 30
    onset = next((days[i] for i in range(first, len(days) - 4)
                  if mm[i] >= 5 and sum(mm[i:i + 5]) >= 25), None)
    if onset is None or (onset - timedelta(days=1)).isoformat() != row["value"]:
        raise ValueError(f"{site}: rainfall totals do not reproduce the supplied last dry day")
    return onset.isoformat()


def make_entries(args, upstream):
    entries, held, pending = {}, set(), []
    checks = set(args.check or CHECKS)

    def add(site, prefix, module, results, source_track=None):
        for suffix, (value, unit, note) in results.items():
            if value is None:
                continue
            if not math.isfinite(value):
                raise ValueError(f"Non-finite metric: {suffix}")
            key = f"track5_{site}_{prefix}{suffix}"
            if key in entries:
                raise ValueError(f"Duplicate metric: {key}")
            if suffix in FOREST_KEYS:
                reference = f"{FOREST_KEYS[suffix]}_{source_track}"
                if reference in upstream:
                    difference = abs(value - upstream[reference]["value"])
                    match = "Agrees with" if difference <= 0.001 else "DIFFERS from"
                    if difference > 0.001:
                        held.add(key)
                        pending.append(f"{key}: outside the 0.001 dB tolerance for {reference}; review before release")
                    note += f" {match} {reference} at tolerance 0.001 dB (absolute difference {difference:.6g} dB)."
            entries[key] = dict(value=value, unit=unit, site=site,
                                made_by=f"pipeline/checks/{module}.py", note=note)
            if module == "recovery" and site in args.onsets:
                entries[key]["note"] += f". Onset {args.onsets[site]}; source: {args.onset_sources[site]}."
            if module == "recovery" and site not in args.onsets:
                held.add(key)

    for site in ("west", "east"):
        if "orbit" in checks:
            add(site, "", "two_orbit", two_orbit.calculate(args.layers, site))
        for track in ("125", "061"):
            if "forest" in checks and site == "west":
                add(site, track + "_", "forest", forest.calculate(args.layers, track), track)
            if "shuffle" in checks:
                add(site, track + "_", "date_shuffle",
                    date_shuffle.calculate(args.stacks, args.layers, site, track))
            if "recovery" in checks:
                folder = args.recovery_layers or args.layers
                files = [folder / f"recovery_{pol}_{site}_{track}.tif" for pol in ("hh", "hv")]
                if not any(p.exists() for p in files):
                    pending.append(f"{site} orbit {track}: no recovery pair available")
                    continue
                if args.recovery_layers is None:
                    # The upstream producer skips a track with no later pass. Its old
                    # TIFFs can survive a rebuild in the same directory.
                    with rasterio.open(args.layers / f"drydown_{site}_{track}.tif") as src:
                        cutoff = src.tags()["dry_until"]
                    with np.load(args.stacks / f"{site}_{track}.npz") as stack:
                        later = sorted(str(d) for d in stack["dates"] if str(d) > cutoff)
                    if not later:
                        pending.append(f"{site} orbit {track}: no pass after {cutoff} in current stack")
                        continue
                    with rasterio.open(files[0]) as src:
                        if src.tags().get("after_pass") != later[0]:
                            raise ValueError(f"{files[0].name}: rebound does not use first later pass in current stack")
                if site in args.onsets and not (args.layers / f"rain_daily_{site}.json").is_file():
                    raise ValueError(f"Missing rainfall file for {site}")
                add(site, "", "recovery", recovery.calculate(args.layers, site, track, args.onsets.get(site), folder))
                audit = recovery.audit_hv_absolute(args.stacks, args.layers, site, track, folder)
                if audit["available"]:
                    suffixes, reason = audit["hold_suffixes"], audit["note"]
                else:
                    suffixes = audit.get("unverified_suffixes") or [
                        f"recovery_{track}_hv_{k}" for k in ("median_db", "driest_decile_median_db")]
                    reason = f"Absolute HV could not be verified: {audit['reason']}."
                for suffix in suffixes:
                    key = f"track5_{site}_{suffix}"
                    held.add(key)
                    entries[key]["note"] += f" HELD: {reason}"
                if suffixes:
                    pending.append(f"{site} {track}: {', '.join(suffixes)} exploratory. {reason}")
        if "peat" in checks:
            maps = ("official", "cifor", "peatmap")
            missing = [name for name in maps
                       if not (args.layers / f"peat_{name}_{site}.tif").is_file()]
            if missing:
                pending.append(f"{site}: missing peat mask(s): {', '.join(missing)}")
            if len(missing) < len(maps):
                add(site, "", "peat_split", peat_split.calculate(args.layers, site))
        if "recovery" in checks and site not in args.onsets:
            pending.append(f"{site}: rainfall onset unconfirmed; fixed-date recovery remains exploratory")
    return entries, held, pending


def persist(path, seed_path, checks, entries, held, verify, compare_previous=True):
    """Serialize Track 5 writers, preserve unrelated entries and replace the JSON atomically."""
    owners = {"orbit": "two_orbit", "forest": "forest", "shuffle": "date_shuffle",
              "recovery": "recovery", "peat": "peat_split"}
    selected = {f"pipeline/checks/{owners[c]}.py" for c in checks}
    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / f".{path.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = json.loads(path.read_text()) if path.exists() else {}
        base = json.loads(seed_path.read_text()) if seed_path else {}
        for k, v in old.items():
            if k in base and base[k] != v and not k.startswith("track5_"):
                raise ValueError(f"{k} differs between local output and seed. Reconcile the other track's entry first.")
            base[k] = v
        keep = {k: v for k, v in base.items()
                if not (k.startswith("track5_") and v.get("made_by") in selected)}
        if verify and compare_previous:
            previous_keys = {k for k, v in old.items()
                             if k.startswith("track5_") and v.get("made_by") in selected}
            if previous_keys != entries.keys():
                raise ValueError("Check coverage changed or there is no first run; review an exploratory rerun first.")
        with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
            staged = Path(tmp) / path.name
            staged.write_text(json.dumps(keep, allow_nan=False))
            for key, row in entries.items():
                status = "final" if verify and key not in held else "exploratory"
                written = vjson.put(key, **row, status=status, path=staged)
                if verify and compare_previous:
                    prior = old.get(key, {})
                    if any(prior.get(f) != v for f, v in written.items() if f != "status"):
                        raise ValueError(f"{key} changed or has no first run. Review the exploratory output first.")
            staged.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=CHECKS, action="append", help="omit to run all five checks")
    parser.add_argument("--stacks", type=Path, default=Path("pipeline/out/stacks"))
    parser.add_argument("--layers", type=Path, default=Path("pipeline/out/layers"))
    parser.add_argument("--seed", type=Path, help="read-only team release validation.json")
    parser.add_argument("--recovery-layers", type=Path, help="folder with orbit-keyed recovery TIFFs")
    parser.add_argument("--rain-onset", default=os.environ.get("TRACK5_RAIN_ONSET", ""),
                        help="Track 3 onsets as west=YYYY-MM-DD,east=YYYY-MM-DD; list only confirmed sites")
    parser.add_argument("--rain-source", default=os.environ.get("TRACK5_RAIN_SOURCE"),
                        help="Track 3 handoff or dataset reference identifying those first-rain dates")
    parser.add_argument("--output", type=Path, default=Path("pipeline/out/validation.json"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="compare with previous run and promote eligible entries")
    mode.add_argument("--repeat", action="store_true", help="compute twice, as in the team pipeline")
    args = parser.parse_args()
    args.onsets = {}
    if args.rain_onset:
        if not args.rain_source:
            parser.error("identify the Track 3 onset determination with --rain-source")
        for item in args.rain_onset.split(","):
            site, sep, day = item.partition("=")
            if not sep or site not in ("west", "east") or site in args.onsets:
                parser.error("use west=YYYY-MM-DD,east=YYYY-MM-DD, listing each confirmed site once")
            try:
                args.onsets[site] = date.fromisoformat(day).isoformat()
            except ValueError:
                parser.error(f"invalid onset date: {day}")
    if args.seed and args.output.resolve() == args.seed.resolve():
        parser.error("use a separate output to preserve the release seed")
    upstream_path = args.seed or args.output
    upstream = json.loads(upstream_path.read_text()) if upstream_path.exists() else {}
    args.onset_sources = {site: args.rain_source for site in args.onsets}
    if not args.check or "recovery" in args.check:
        for site in ("west", "east"):
            onset = released_onset(args.layers, site, upstream)
            if onset is None:
                continue
            if site in args.onsets and args.onsets[site] != onset:
                parser.error(f"{site}: supplied onset conflicts with the rainfall record")
            args.onsets[site] = onset
            args.onset_sources[site] = f"last_dry_day_{site}, verified against {site} daily IMERG totals"
    first = make_entries(args, upstream)
    if args.repeat:
        second = make_entries(args, upstream)
        if first != second:
            raise ValueError("Independent runs differ. Existing validation output was preserved.")
    entries, held, pending = first
    verified = args.repeat or args.verify
    persist(args.output, args.seed, args.check or CHECKS, entries, held, verified,
            compare_previous=not args.repeat)
    print(f"{len(entries)} Track 5 entries; {len(entries) - len(held) if verified else 0} final")
    for message in pending:
        print(message)


if __name__ == "__main__":
    main()
