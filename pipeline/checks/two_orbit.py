# Written with Super Intelligence (SI) assistance.
"""Agreement between orbit 125 and orbit 061 on their common footprint."""
import numpy as np
from scipy.stats import pearsonr, spearmanr

from pipeline.checks.common import centres, read_drydown, same_grid


def agreement(ascending, descending):
    if ascending.shape != descending.shape:
        raise ValueError("Different input shapes")
    valid = np.isfinite(ascending) & np.isfinite(descending)
    a, b = ascending[valid], descending[valid]
    n = a.size
    if n < 10 or np.ptp(a) == 0 or np.ptp(b) == 0:
        raise ValueError("Need at least ten paired blocks and variation on both tracks")
    k = n // 10
    # Stable sorting retains raster row order for ties at the boundary.
    ia = np.argsort(a, kind="stable")[:k]
    ib = np.argsort(b, kind="stable")[:k]
    shared = np.intersect1d(ia, ib, assume_unique=True).size
    notes = "Paired complete 250 m blocks across the common radar footprint; orbits 125 and 061."
    decile = f"{shared} of {k} track-125 blocks; lowest floor(n/10) per orbit; ties in row-major order. Whole-site agreement diagnostic."
    return {
        "orbit_pearson": (float(pearsonr(a, b).statistic), "Pearson r", notes),
        "orbit_spearman": (float(spearmanr(a, b).statistic), "Spearman rho", notes),
        "orbit_blocks": (int(n), "paired blocks", notes),
        "orbit_driest_tenth_overlap": (shared / k, "fraction of track-125 driest tenth", decile),
    }


def calculate(layers, site):
    a, ga, ta = read_drydown(layers, site, "125")
    b, gb, tb = read_drydown(layers, site, "061")
    if ta["dry_until"] != tb["dry_until"]:
        raise ValueError(f"{site}: orbit dry-down layers use different seasonal cutoffs")
    same_grid(ga, gb)
    results = agreement(centres(a), centres(b))
    period = f" Seasonal cutoff {ta['dry_until']}; first/late 125 passes {ta['first_passes']}/{ta['late_passes']}; 061 passes {tb['first_passes']}/{tb['late_passes']}."
    return {k: (v, unit, note + period) for k, (v, unit, note) in results.items()}
