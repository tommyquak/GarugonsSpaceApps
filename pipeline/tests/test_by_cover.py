# Written with Super Intelligence (SI) assistance.
"""by_cover: peat is sorted into HV classes, and each class gets its own share and fall."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "drying"))
from by_cover import by_class  # noqa: E402


def test_classes_split_the_peat_and_keep_their_own_fall():
    hv = np.array([[-18.0, -18.0, -10.0, -10.0], [-14.0, -12.0, -10.0, np.nan]])
    dawn = np.array([[-2.0, -1.5, 0.0, 0.1], [-1.2, -0.4, 0.0, -3.0]])
    dusk = np.array([[-1.1, -0.5, 0.0, 0.0], [-1.0, -0.3, 0.1, -3.0]])
    peat = np.ones_like(hv, bool)
    peat[0, 3] = False                      # one closed-forest cell is off peat and must not count
    rows = by_class(hv, [dawn, dusk], peat)
    assert abs(sum(r["share"] for r in rows.values()) - 1) < 1e-9
    assert rows["hv_below_m15"]["share"] == 2 / 6
    assert rows["hv_below_m15"]["fell"] == 0.5          # only one of the two fell on both orbits
    assert rows["hv_m15_m13"]["fell"] == 1.0
    assert rows["hv_above_m11"]["fell"] == 0.0
    assert rows["hv_above_m11"]["medians"] == [0.0, 0.05]


def test_cells_without_data_are_left_out():
    hv = np.array([[np.nan, -10.0]])
    rows = by_class(hv, [np.array([[-5.0, 0.0]]), np.array([[-5.0, 0.0]])], np.ones((1, 2), bool))
    assert list(rows) == ["hv_above_m11"] and rows["hv_above_m11"]["share"] == 1.0
