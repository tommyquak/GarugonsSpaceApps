# Written with Super Intelligence (SI) assistance.
"""Figures for the slides and the project page, drawn from the pipeline's own outputs.

Every figure is 1600 by 900 pixels, carries the source of its data and a line saying it was
made with SI assistance, and can be redrawn at any time. Numbers are read from the layers
and from validation.json, never typed.

  fig_season.png      the season at a glance: HH on the land that fell, pass by pass, with daily rain
  fig_orbits.png      the two orbits' dry-down maps side by side, and how they compare block by block
  fig_start.png       why the start matters: the fall measured from the rain-wet start and from the dry start
  fig_recovery.png    after the rain: HH and HV still below the start, with and without fire detections
  fig_edge.png        the fall by distance into the forest

    python pipeline/figures.py --out pipeline/out/figures
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "drying"))
from common import load_reference  # noqa: E402
from season import start_passes  # noqa: E402

L, S = Path("pipeline/out/layers"), Path("pipeline/out/stacks")
INK, MUTED, GRID = "#1b1f23", "#5b6570", "#d9dee3"
DAWN, DUSK, RAIN, FIRE, FOREST = "#b9742f", "#5a3a1c", "#3f8fd6", "#de3626", "#3d8b63"
MARK = "Made with Super Intelligence (SI) assistance from NASA and ISRO NISAR L2 GCOV data"


def read(path):
    with rasterio.open(path) as src:
        return src.read(1)


def day(yyyymmdd):
    return dt.date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:]))


def frame(title, subtitle):
    fig = plt.figure(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor("white")
    fig.text(0.05, 0.93, title, fontsize=24, fontweight="bold", color=INK, ha="left")
    fig.text(0.05, 0.885, subtitle, fontsize=14, color=MUTED, ha="left")
    return fig


def finish(fig, path, source):
    fig.text(0.05, 0.048, f"Data: {source}. Exploratory, one season, no ground measurements.", fontsize=10.5, color=MUTED, ha="left")
    fig.text(0.05, 0.022, MARK, fontsize=10.5, color=MUTED, ha="left")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print("wrote", path)


def tidy(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=12)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def pass_series(site, track, mask):
    """Median over `mask` of every per-pass layer of one orbit, as (dates, values)."""
    files = sorted(L.glob(f"hh_{site}_{track}_*.tif"))
    dates = [day(f.stem.split("_")[-1]) for f in files]
    return dates, [float(np.nanmedian(read(f)[mask])) for f in files]


def fig_season(out, v):
    site = "west"
    fell = (read(L / f"drydown_{site}_125.tif") <= -1) & (read(L / f"drydown_{site}_061.tif") <= -1) & (read(L / f"peat_peatmap_{site}.tif") == 1)
    ref = load_reference(L)
    rain = json.loads((L / f"rain_daily_{site}.json").read_text())
    fig = frame("The season in one picture", "West box. Peat where HH fell by 1 dB or more on both orbits, against deep forest, with daily rain.")
    ax = fig.add_axes([0.07, 0.36, 0.86, 0.46])
    for track, colour, name in (("125", DAWN, "dawn orbit"), ("061", DUSK, "dusk orbit")):
        d, y = pass_series(site, track, fell)
        ax.plot(d, y, "-o", color=colour, linewidth=2.5, markersize=7, label=f"Land that fell, {name}")
        ax.annotate(name, (d[-2], y[-2]), textcoords="offset points", xytext=(-8, -18 if track == "125" else 12), color=colour, fontsize=12, ha="right")
        dr, yr = pass_series(site, track, ref)
        ax.plot(dr, yr, "-", color=FOREST, linewidth=1.6, alpha=0.9)
    ax.annotate("deep forest (the yardstick)", (day("20260902"), 0.0), textcoords="offset points", xytext=(0, 9), color=FOREST, fontsize=12)
    first_dry, last_dry = dt.date.fromisoformat(v["first_dry_day_west"]["value"]), dt.date.fromisoformat(v["last_dry_day_west"]["value"])
    ax.axvspan(first_dry, last_dry, color="#f4e3b1", alpha=0.35, linewidth=0)
    ax.text(first_dry + dt.timedelta(40), ax.get_ylim()[0] * 0.96, "dry season by the rainfall rule", color="#8b5a2b", fontsize=12, va="bottom")
    ax.axhline(0, color=GRID, linewidth=1)
    ax.set_ylabel("HH against the dry start, dB", fontsize=13, color=MUTED)
    ax.set_xlim(dt.date(2026, 6, 10), dt.date(2026, 11, 10))
    tidy(ax)
    ax.tick_params(labelbottom=False)
    ax2 = fig.add_axes([0.07, 0.14, 0.86, 0.19], sharex=ax)
    days = [dt.date.fromisoformat(k) for k in sorted(rain)]
    ax2.bar(days, [rain[k] for k in sorted(rain)], color=RAIN, width=1.0)
    ax2.set_ylabel("Rain, mm per day", fontsize=13, color=MUTED)
    tidy(ax2)
    import matplotlib.dates as mdates
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    finish(fig, out / "fig_season.png", "NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC), PEATMAP")


def fig_orbits(out, v):
    site = "west"
    a, d = read(L / f"drydown_{site}_125.tif"), read(L / f"drydown_{site}_061.tif")
    fig = frame("Two orbits, one answer", "West box. The change in HH from the dry start to mid October, seen from opposite sides at dawn and at dusk.")
    from matplotlib.colors import LinearSegmentedColormap
    ramp = LinearSegmentedColormap.from_list("fall", ["#4e2f17", "#8b5a2b", "#bd8a4a", "#e0bd7c", "#f7f3ea", "#cfe3f3"])
    for k, (img, name) in enumerate(((a, "Dawn orbit, track 125"), (d, "Dusk orbit, track 061"))):
        ax = fig.add_axes([0.05 + 0.3 * k, 0.2, 0.28, 0.62])
        im = ax.imshow(img[::3, ::3], cmap=ramp, vmin=-3, vmax=1, interpolation="nearest")
        ax.set_title(name, fontsize=14, color=INK, loc="left")
        ax.axis("off")
    cax = fig.add_axes([0.05, 0.165, 0.58, 0.014])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label("Change in HH, dB (brown is a fall)", fontsize=12, color=MUTED)
    cb.ax.tick_params(colors=MUTED, labelsize=11)
    ax = fig.add_axes([0.71, 0.24, 0.24, 0.52])
    k = np.isfinite(a) & np.isfinite(d)
    pick = np.zeros_like(k)
    pick[2::5, 2::5] = True
    k &= pick
    ax.hexbin(a[k], d[k], gridsize=60, extent=(-4, 2, -4, 2), cmap="Greys", bins="log", linewidths=0)
    ax.plot([-4, 2], [-4, 2], color=FIRE, linewidth=1.2)
    r = float(np.corrcoef(a[k], d[k])[0, 1])
    ax.set_xlabel("Dawn orbit, dB", fontsize=13, color=MUTED)
    ax.set_ylabel("Dusk orbit, dB", fontsize=13, color=MUTED)
    ax.set_title(f"Block by block, r = {r:.2f}", fontsize=14, color=INK, loc="left")
    tidy(ax)
    ax.set_aspect("equal")
    finish(fig, out / "fig_orbits.png", "NISAR L2 GCOV (ASF DAAC)")


def fig_start(out, v):
    sens = json.loads((L / "sensitivity.json").read_text())
    rows = [("From the first two passes\n(taken just after rain)", "start: the first two passes of the record (taken after rain)", "#b9b0a3"),
            ("From the first rain-free passes\n(what we report)", "default: HH, start by the rain rule, last two dry passes, 250 m", DUSK),
            ("One pass later still", "start: one pass later than the rule", "#b9b0a3")]
    fig = frame("Why the starting point matters", "West box. Share of all land where HH fell by 1 dB or more on both orbits, for three choices of start.")
    ax = fig.add_axes([0.3, 0.2, 0.6, 0.6])
    vals = [100 * sens[key]["share_1db_both"] for _, key, _ in rows]
    bars = ax.barh([r[0] for r in rows][::-1], vals[::-1], color=[r[2] for r in rows][::-1], height=0.55)
    for b, val in zip(bars, vals[::-1]):
        ax.text(val + 0.5, b.get_y() + b.get_height() / 2, f"{val:.0f}%", va="center", fontsize=15, color=INK)
    ax.set_xlabel("Share of the box, %", fontsize=13, color=MUTED)
    tidy(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.tick_params(axis="y", labelsize=14, colors=INK)
    fig.text(0.3, 0.115, "An independent audit found our first start was rain-wet. The start is now chosen from the rainfall record by a fixed rule.", fontsize=12.5, color=MUTED)
    finish(fig, out / "fig_start.png", "NISAR L2 GCOV (ASF DAAC), GPM IMERG (GES DISC)")


def fig_recovery(out, v):
    fig = frame("After the first rain", "West box, peat that fell by 1 dB or more. How far below the dry start it still was on the first pass after the rain.")
    groups = [("HH, no fire detected", "recovery_hh_median_left_on_peat_no_fire_west_{t}", "#8cb7de"), ("HH, fire detected", "recovery_hh_median_left_on_peat_fire_west_{t}", "#f0a69d"),
              ("HV, no fire detected", "recovery_hv_median_left_on_peat_no_fire_west_{t}", RAIN), ("HV, fire detected", "recovery_hv_median_left_on_peat_fire_west_{t}", FIRE)]
    ax = fig.add_axes([0.1, 0.2, 0.8, 0.6])
    x, width = np.arange(2), 0.19
    for i, (name, key, colour) in enumerate(groups):
        vals = [-v[key.format(t=t)]["value"] for t in ("125", "061")]
        bars = ax.bar(x + (i - 1.5) * width, vals, width * 0.92, color=colour, label=name)
        for b, val in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.015, f"{val:.2f}", ha="center", fontsize=12, color=INK)
    ax.set_xticks(x, ["Dawn orbit, pass of 1 Nov", "Dusk orbit, pass of 28 Oct"], fontsize=14, color=INK)
    ax.set_ylabel("Still below the dry start, dB", fontsize=13, color=MUTED)
    ax.legend(frameon=False, fontsize=13, ncols=4, loc="upper center", bbox_to_anchor=(0.5, 1.1))
    tidy(ax)
    fig.text(0.1, 0.115, "One pass per orbit, within days of heavy rain, from a later processing release than the dry passes. HV here carries the forest baseline; see docs/LIMITS.md.", fontsize=12, color=MUTED)
    finish(fig, out / "fig_recovery.png", "NISAR L2 GCOV (ASF DAAC), NASA FIRMS, PEATMAP")


def fig_edge(out, v):
    depth = read(L / "forest_depth_west.tif")
    pick = np.zeros(depth.shape, bool)
    pick[2::5, 2::5] = True
    bins = [(0.05, 0.25), (0.25, 0.5), (0.5, 1), (1, 2), (2, 4), (4, 6), (6, 99)]
    labels = ["under 250 m", "250 to 500 m", "0.5 to 1 km", "1 to 2 km", "2 to 4 km", "4 to 6 km", "over 6 km"]
    fig = frame("Forest edges fall too", "West box. Median change in HH over the dry season by distance into the forest, on both orbits.")
    ax = fig.add_axes([0.1, 0.2, 0.8, 0.6])
    x, width = np.arange(len(bins)), 0.38
    for i, (track, colour, name) in enumerate((("125", DAWN, "Dawn orbit"), ("061", DUSK, "Dusk orbit"))):
        score = read(L / f"drydown_west_{track}.tif")
        vals = [float(np.median(score[pick & (depth >= lo) & (depth < hi) & np.isfinite(score)])) for lo, hi in bins]
        ax.bar(x + (i - 0.5) * width, vals, width * 0.94, color=colour, label=name)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_xticks(x, labels, fontsize=13, color=INK)
    ax.set_xlabel("Distance from the forest edge", fontsize=13, color=MUTED)
    ax.set_ylabel("Median change in HH, dB", fontsize=13, color=MUTED)
    ax.legend(frameon=False, fontsize=13, loc="lower right")
    tidy(ax)
    fig.text(0.1, 0.115, "Deep forest is the yardstick, so it is zero by construction. Whether the edge effect is drying or degraded forest is open.", fontsize=12, color=MUTED)
    finish(fig, out / "fig_edge.png", "NISAR L2 GCOV (ASF DAAC)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    v = json.loads(Path("pipeline/out/validation.json").read_text())
    for make in (fig_season, fig_orbits, fig_start, fig_recovery, fig_edge):
        make(a.out, v)


if __name__ == "__main__":
    main()
