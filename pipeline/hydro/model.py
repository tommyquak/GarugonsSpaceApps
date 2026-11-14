# Written with Super Intelligence (SI) assistance.
"""A four-number water-table model, fitted to real gauge records and then run on 2026 rainfall.

There are no water-level measurements for 2026, the year NISAR observed. There are daily
records for 2013 to 2018 at two sites nearby (gauges.py). This model learns from those years
how the water table answers rain, is tested on years it was not fitted to, and is then driven
by 2026 rainfall to give a modelled water table for the weeks the radar saw.

The model, one step per day, level in metres relative to the ground (negative is below it):

    level = level + rise * rain - loss - pull * level        then capped at "top"

  rise   metres of rise per millimetre of rain (one over a thousand times the specific yield)
  loss   metres lost per day to evaporation and drainage when the water table is at the surface
  pull   how fast the loss shrinks as the water table falls (the level is negative below ground,
         so this term adds water back: deep water tables lose less)
  top    the highest the water can stand above the ground before it runs off

It is a bucket, not hydrology: no lateral flow, no canal, no change in peat properties with
depth. Its output for 2026 is a modelled value and must always be labelled so.

Testing: for each site, each year in turn is left out of the fit, and the model is then run
freely through the whole record from its first day; skill is measured on the left-out year.

Writes water_table_model.json (numbers, skill) and water_table_modelled.json (daily levels
for the gauge years and for 2026), and entries in validation.json.

    python pipeline/hydro/model.py --hydro pipeline/out/hydro --year 2026
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vjson import put  # noqa: E402

ME = "pipeline/hydro/model.py"
CONFIG = json.loads((Path(__file__).parent / "sites.json").read_text())
START = np.array([0.004, 0.012, 0.010, 0.10])       # rise, loss, pull, top
LIMIT_M = -0.40                                     # the regulatory water-table limit in peat


def simulate(params, rain, first_level):
    rise, loss, pull, top = params
    level, out = first_level, np.empty(len(rain))
    for i, mm in enumerate(rain):
        level = min(level + rise * mm - loss - pull * level, top)
        out[i] = level
    return out


def fit(rain, observed, use):
    """Least-squares fit on the days marked True in `use`. Returns the four numbers."""
    first = observed[np.isfinite(observed)][0]

    def cost(params):
        if params[0] <= 0 or params[1] < 0 or params[2] < 0 or params[3] < -0.2:
            return 1e6
        sim = simulate(params, rain, first)
        return float(np.sqrt(np.nanmean((sim[use] - observed[use]) ** 2)))

    best = minimize(cost, START, method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-5, "maxiter": 4000})
    return best.x


def skill(sim, observed, mask):
    k = mask & np.isfinite(observed)
    if k.sum() < 30:
        return None
    return {"days": int(k.sum()), "r": round(float(np.corrcoef(sim[k], observed[k])[0, 1]), 3),
            "rmse_m": round(float(np.sqrt(np.mean((sim[k] - observed[k]) ** 2))), 3),
            "lowest_observed_m": round(float(observed[k].min()), 2), "lowest_modelled_m": round(float(sim[k].min()), 2)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hydro", required=True, type=Path, help="folder with gauge_daily.json and rain_gauges.json")
    p.add_argument("--year", type=int, default=2026, help="the year to model with no gauge data")
    a = p.parse_args()
    gauges = json.loads((a.hydro / "gauge_daily.json").read_text())
    rain_all = json.loads((a.hydro / "rain_gauges.json").read_text())
    summary, series = {}, {}
    for site, record in gauges.items():
        days = sorted(record)
        first, last = dt.date.fromisoformat(days[0]), dt.date.fromisoformat(days[-1])
        span = [first + dt.timedelta(n) for n in range((last - first).days + 1)]
        missing_rain = sum(d.isoformat() not in rain_all for d in span)
        if missing_rain:
            raise SystemExit(f"{site}: rainfall is missing for {missing_rain} days of the gauge record; run rain_history.py first")
        rain = np.array([rain_all[d.isoformat()] for d in span])
        observed = np.array([record.get(d.isoformat(), np.nan) for d in span])
        years = np.array([d.year for d in span])
        have = np.isfinite(observed)

        held_out = {}
        for year in sorted(set(years[have])):
            if (have & (years == year)).sum() < 120:      # too short a year to test on
                continue
            params = fit(rain, observed, have & (years != year))
            held_out[str(year)] = skill(simulate(params, rain, observed[have][0]), observed, years == year)
        params = fit(rain, observed, have)
        sim = simulate(params, rain, observed[have][0])
        summary[site] = {"title": CONFIG["sites"][site]["title"], "record": f"{days[0]} to {days[-1]}",
                         "rise_m_per_mm": round(float(params[0]), 5), "loss_m_per_day": round(float(params[1]), 5),
                         "pull_per_day": round(float(params[2]), 5), "top_m": round(float(params[3]), 3),
                         "specific_yield": round(1 / (1000 * float(params[0])), 2),
                         "fit_all_years": skill(sim, observed, np.ones(len(span), bool)), "held_out_years": held_out}
        rs = [v["r"] for v in held_out.values() if v]
        errs = [v["rmse_m"] for v in held_out.values() if v]
        put(f"hydro_held_out_r_min_{site}", min(rs), "Pearson r", "gauges", ME, note=f"worst left-out year of {len(rs)}; daily water table, {CONFIG['sites'][site]['title'].lower()}")
        put(f"hydro_held_out_r_max_{site}", max(rs), "Pearson r", "gauges", ME)
        put(f"hydro_held_out_rmse_max_m_{site}", max(errs), "m", "gauges", ME, note="largest error on a left-out year")

        # The year with no gauges: start the year at the surface (wet season) and let the model run.
        y0, y1 = dt.date(a.year, 1, 1), max(dt.date.fromisoformat(d) for d in rain_all if d.startswith(str(a.year)))
        span_y = [y0 + dt.timedelta(n) for n in range((y1 - y0).days + 1)]
        rain_y = np.array([rain_all.get(d.isoformat(), 0.0) for d in span_y])
        sim_y = simulate(params, rain_y, 0.0)
        below = sim_y < LIMIT_M
        first_below = span_y[int(np.argmax(below))].isoformat() if below.any() else None
        summary[site][f"modelled_{a.year}"] = {"days_below_limit": int(below.sum()), "first_day_below_limit": first_below,
                                               "lowest_m": round(float(sim_y.min()), 2), "lowest_on": span_y[int(np.argmin(sim_y))].isoformat()}
        put(f"hydro_modelled_days_below_40cm_{a.year}_{site}", int(below.sum()), "days", "gauges", ME,
            note=f"MODELLED, not measured: water table below 0.4 m, driven by {a.year} rainfall; first such day {first_below}")
        put(f"hydro_modelled_lowest_m_{a.year}_{site}", float(sim_y.min()), "m", "gauges", ME, note="MODELLED, not measured")
        series[site] = {"gauge_years": {d.isoformat(): round(float(v), 3) for d, v in zip(span, sim)},
                        str(a.year): {d.isoformat(): round(float(v), 3) for d, v in zip(span_y, sim_y)}}
        print(f"{site}: specific yield {summary[site]['specific_yield']}, fit r {summary[site]['fit_all_years']['r']} rmse {summary[site]['fit_all_years']['rmse_m']} m; "
              f"left-out years: " + ", ".join(f"{y} r {v['r']} rmse {v['rmse_m']}" for y, v in held_out.items() if v) +
              f"; {a.year} modelled: {int(below.sum())} days below 0.4 m from {first_below}, lowest {sim_y.min():.2f} m")
    (a.hydro / "water_table_model.json").write_text(json.dumps({"model": "level = level + rise * rain - loss - pull * level, capped at top",
                                                               "label": "modelled, not measured", "sites": summary}, indent=1) + "\n")
    (a.hydro / "water_table_modelled.json").write_text(json.dumps(series) + "\n")


if __name__ == "__main__":
    main()
