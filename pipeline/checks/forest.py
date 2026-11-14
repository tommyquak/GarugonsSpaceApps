# Written with Super Intelligence (SI) assistance.
"""Spread of dry-down scores inside the shared west forest reference."""
import numpy as np

from pipeline.checks.common import centres, read_drydown, read_grid, same_grid


def forest_metrics(change, mask):
    if mask.shape != change.shape or not np.isin(mask[np.isfinite(mask)], [0, 1]).all():
        raise ValueError("Expected a matching binary reference forest")
    rows, cols = mask.shape
    blocks = mask[:rows // 5 * 5, :cols // 5 * 5].reshape(rows // 5, 5, cols // 5, 5)
    inside = (blocks == 1).sum(axis=(1, 3)) >= 24
    scores = centres(change)
    v = scores[inside & np.isfinite(scores)]
    if not v.size:
        raise ValueError("No valid reference blocks")
    note = "Shared west reference, >=24/25 forest pixels, full 250 m blocks. Internal stability; p05 is the drying threshold."
    result = {"forest_blocks": (int(v.size), "reference blocks", note)}
    for q, value in zip((5, 50, 95), np.percentile(v, [5, 50, 95])):
        result[f"forest_p{q:02}"] = (float(value), "dB", note)
    return result


def calculate(layers, track):
    change, gc, tags = read_drydown(layers, "west", track)
    mask, gm = read_grid(layers / "reference_west.tif")
    same_grid(gc, gm)
    results = forest_metrics(change, mask)
    period = f" Track {track} through {tags['dry_until']}; first/late passes {tags['first_passes']}/{tags['late_passes']}."
    return {k: (v, unit, note + period) for k, (v, unit, note) in results.items()}
