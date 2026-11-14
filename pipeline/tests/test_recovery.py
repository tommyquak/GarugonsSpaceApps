# Written with Super Intelligence (SI) assistance.
"""Tests for recovery after the rain on a small synthetic stack where the right answer is known."""
import json
import sys

import numpy as np
import pytest
import rasterio

import common
import recovery

DRY_UNTIL = "20260731"
DATES = ("20260601", "20260613", "20260625", "20260707", "20260719", "20260731", "20260812", "20260824")
HH_BACK, HV_BACK = 1.5, 0.5   # what the first wet pass brings back on the drying half


def make_stack(rows=60, cols=60):
    """Flat ground. The right half falls by 2 dB over the six dry passes, then the first wet pass brings back
    1.5 dB in HH and 0.5 dB in HV. The last pass is soaked (+5 dB) and must never be used. Each date carries a scene-wide shift."""
    n_dry = 6
    shift = np.array([0.3, -0.2, 0.1, -0.4, 0.2, 0.0, 0.25, -0.15], "float32")
    fall = np.linspace(0, -2, n_dry).astype("float32")
    right = {"hh": np.concatenate([fall, [fall[-1] + HH_BACK, 5.0]]), "hv": np.concatenate([fall, [fall[-1] + HV_BACK, 5.0]])}
    stack = {"cov": np.ones((rows, cols), bool), "T": rasterio.Affine(50, 0, 500000, 0, -50, 9700000), "epsg": 32750, "dates": list(DATES)}
    for pol, level in (("hh", -6.0), ("hv", -12.0)):
        a = np.full((len(DATES), rows, cols), level, "float32") + shift[:, None, None]
        a[:, :, cols // 2:] += right[pol].astype("float32")[:, None, None]
        stack[pol] = a
    off = (shift - shift.mean()).tolist()
    baseline = {"dates": list(DATES), "hh": {"offset_db": off}, "hv": {"offset_db": off}}
    expected_fall = float(fall[-2:].mean() - fall[:2].mean())
    expected_rebound = {"hh": float(fall[-1] + HH_BACK - fall[-2:].mean()), "hv": float(fall[-1] + HV_BACK - fall[-2:].mean())}
    return stack, baseline, expected_fall, expected_rebound


def test_no_pass_after_the_rain_gives_none():
    stack, baseline, _, _ = make_stack()
    assert recovery.recover(stack, baseline, "20260824") is None


def test_too_few_dry_passes_is_refused():
    stack, baseline, _, _ = make_stack()
    with pytest.raises(SystemExit):
        recovery.recover(stack, baseline, "20260625")


def test_uses_the_first_pass_after_the_rain_only():
    stack, baseline, _, _ = make_stack()
    _, dry, after = recovery.recover(stack, baseline, DRY_UNTIL)
    assert dry == [0, 1, 2, 3, 4, 5] and after == 6


def test_fall_rebound_and_left_on_a_known_stack():
    stack, baseline, fall, rebound = make_stack()
    out, _, _ = recovery.recover(stack, baseline, DRY_UNTIL)
    for pol in ("hh", "hv"):
        o = out[pol]
        for k in ("fall", "rebound", "left"):
            assert abs(o[k][30, 10]) < 1e-4, (pol, k)                 # stable half, scene shift removed
        assert np.isclose(o["fall"][30, 50], fall, atol=1e-4)
        assert np.isclose(o["rebound"][30, 50], rebound[pol], atol=1e-4)
        assert np.allclose(o["left"], o["fall"] + o["rebound"], atol=1e-5, equal_nan=True)
    assert out["hh"]["rebound"][30, 50] > out["hv"]["rebound"][30, 50]   # HH comes back more than HV


def test_strong_blocks_need_the_fall_on_both_orbits():
    stack, baseline, _, _ = make_stack()
    out, _, _ = recovery.recover(stack, baseline, DRY_UNTIL)
    other = np.full(stack["cov"].shape, -2.0, "float32")
    other[40:, :] = 0.0                                               # the other orbit saw no fall in the bottom rows
    ok, strong = recovery.strong_blocks(out, other, stack["cov"])
    assert ok.sum() == 12 * 12                                        # one sample per 250 m block
    assert not strong[:, :30].any() and not strong[40:, :].any()      # stable half, and where the other orbit disagrees
    assert strong[2:40:5, 32::5].all()


def test_summarise_gives_the_share_regained_and_back():
    pol_out = {"fall": np.array([-2.0, -2.0, -2.0]), "rebound": np.array([1.0, 1.5, 2.0])}
    pol_out["left"] = pol_out["fall"] + pol_out["rebound"]
    m = recovery.summarise(pol_out, np.ones(3, bool), floor=0.3)
    assert np.isclose(m["regained"], 0.75)                            # median rebound 1.5 of a median fall of 2
    assert np.isclose(m["back"], 1 / 3)                               # only the block left at 0 dB is within the floor
    assert np.isnan(recovery.summarise({k: -v for k, v in pol_out.items()}, np.ones(3, bool), 0.3)["regained"])


def test_main_writes_layers_and_numbers(tmp_path, monkeypatch):
    stack, baseline, _, rebound = make_stack()
    stacks, layers = tmp_path / "stacks", tmp_path / "layers"
    stacks.mkdir()
    layers.mkdir()
    np.savez(stacks / "west_125.npz", hh=stack["hh"], hv=stack["hv"], cov=stack["cov"], T=np.array(stack["T"])[:6],
             crs=stack["epsg"], dates=np.array(stack["dates"]))
    (layers / "baseline_125.json").write_text(json.dumps(baseline))
    other = np.where(np.arange(60)[None, :] >= 30, -2.0, 0.0) * np.ones((60, 1))
    common.write_layer(layers / "drydown_west_061.tif", other.astype("float32"), stack)
    monkeypatch.chdir(tmp_path)
    vpath = tmp_path / "pipeline/out/validation.json"
    vpath.parent.mkdir(parents=True)
    vpath.write_text(json.dumps({"noise_floor_hh_125": {"value": -0.3}}))
    monkeypatch.setattr(sys, "argv", ["recovery.py", "--site", "west", "--track", "125", "--other-track", "061",
                                      "--dry-until", DRY_UNTIL, "--stacks", str(stacks), "--layers", str(layers)])
    recovery.main()
    with rasterio.open(layers / "recovery_hh_west_125.tif") as src:
        assert np.isclose(src.read(1)[30, 50], rebound["hh"], atol=1e-4)
        assert src.tags()["after_pass"] == "20260812"
    with rasterio.open(layers / "recovery_left_hv_west_125.tif") as src:
        left = src.read(1)
        assert np.isclose(left[30, 50], -1.6 + rebound["hv"], atol=1e-4)    # fall plus rebound: what the rain did not bring back
        assert abs(left[30, 10]) < 1e-4 and src.tags()["start_passes"] == "20260601,20260613"
    v = json.loads(vpath.read_text())
    assert v["recovery_blocks_west_125"]["value"] == 12 * 6           # the right half of the blocks
    assert v["recovery_hh_share_regained_west_125"]["value"] > v["recovery_hv_share_regained_west_125"]["value"]
    assert all(e.get("status", "exploratory") == "exploratory" for e in v.values())


def load_sensitivity():
    """pipeline/recovery/sensitivity.py by path, since pipeline/drying has a module of the same name."""
    import importlib.util
    from pathlib import Path
    path = Path(recovery.__file__).with_name("sensitivity.py")
    spec = importlib.util.spec_from_file_location("recovery_sensitivity", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sensitivity_runs_every_variant_and_flags_a_soaked_pass():
    sens = load_sensitivity()
    stack, baseline, fall, rebound = make_stack()
    other = np.where(np.arange(60)[None, :] >= 30, -2.0, 0.0) * np.ones((60, 1))
    rows = sens.run(stack, baseline, other, 0.3, DRY_UNTIL, min_blocks=10)
    assert [r["variant"] for r in rows] == ["as run", "late one pass", "late earlier", "second wet", "placebo"]
    assert rows[0]["after_pass"] == "20260812" and rows[3]["after_pass"] == "20260824"
    assert rows[4]["dry_until"] == "20260719" and rows[4]["after_pass"] == "20260731"
    assert rows[4]["hh"]["regained"] < 0                               # before the rain the land is still drying: no rebound
    assert np.isclose(rows[0]["hh"]["regained"], rebound["hh"] / -fall, atol=1e-3)   # as run matches recovery.py
    assert sens.largest_move(rows, "hh") > 1.0                        # the +5 dB soaked pass moves the share a lot


def test_late_skip_moves_the_late_pair_back_one_pass():
    stack, baseline, _, _ = make_stack()
    out, _, _ = recovery.recover(stack, baseline, DRY_UNTIL, late_skip=1)
    fall = np.linspace(0, -2, 6)
    assert np.isclose(out["hh"]["fall"][30, 50], fall[3:5].mean() - fall[:2].mean(), atol=1e-4)


def test_placebo_is_not_counted_as_a_variant():
    sens = load_sensitivity()
    rows = [{"variant": "as run", "hh": {"regained": 0.6}}, {"variant": "late one pass", "hh": {"regained": 0.65}},
            {"variant": "placebo", "hh": {"regained": -0.2}}]
    assert np.isclose(sens.largest_move(rows, "hh"), 0.05)


def test_sensitivity_leaves_out_variants_it_cannot_run():
    sens = load_sensitivity()
    stack, baseline, _, _ = make_stack()
    other = np.full((60, 60), -2.0)
    rows = sens.run(stack, baseline, other, 0.3, "20260812", min_blocks=10)   # only one pass after this date
    assert "second wet" not in [r["variant"] for r in rows]


def test_zones_cover_every_cell_once():
    peat = np.array([[True, True], [False, False]])
    fire = np.array([[True, False], [True, False]])
    z = recovery.zones(peat, fire)
    assert sorted(z) == ["off_peat_fire", "off_peat_no_fire", "on_peat_fire", "on_peat_no_fire"]
    assert (sum(m.astype(int) for m in z.values()) == 1).all()
    assert z["on_peat_fire"][0, 0] and z["off_peat_no_fire"][1, 1]


def test_main_splits_by_peat_and_fire_when_the_layers_exist(tmp_path, monkeypatch):
    stack, baseline, _, _ = make_stack()
    stacks, layers = tmp_path / "stacks", tmp_path / "layers"
    stacks.mkdir()
    layers.mkdir()
    np.savez(stacks / "west_125.npz", hh=stack["hh"], hv=stack["hv"], cov=stack["cov"], T=np.array(stack["T"])[:6],
             crs=stack["epsg"], dates=np.array(stack["dates"]))
    (layers / "baseline_125.json").write_text(json.dumps(baseline))
    other = np.where(np.arange(60)[None, :] >= 30, -2.0, 0.0) * np.ones((60, 1))
    common.write_layer(layers / "drydown_west_061.tif", other.astype("float32"), stack)
    peat = np.zeros((60, 60), "float32")
    peat[:30] = 1                                                     # top half is mapped peat
    fire = np.zeros((60, 60), "float32")
    fire[:, 45:] = 3                                                  # right quarter burned
    common.write_layer(layers / "peat_peatmap_west.tif", peat, stack)
    common.write_layer(layers / "fire_days_west.tif", fire, stack)
    monkeypatch.chdir(tmp_path)
    vpath = tmp_path / "pipeline/out/validation.json"
    vpath.parent.mkdir(parents=True)
    vpath.write_text(json.dumps({"noise_floor_hh_125": {"value": -0.3}}))
    monkeypatch.setattr(sys, "argv", ["recovery.py", "--site", "west", "--track", "125", "--other-track", "061",
                                      "--dry-until", DRY_UNTIL, "--stacks", str(stacks), "--layers", str(layers)])
    monkeypatch.setattr(recovery, "MIN_ZONE_BLOCKS", 5)
    recovery.main()
    v = json.loads(vpath.read_text())
    counts = {z: v[f"recovery_blocks_{z}_west_125"]["value"] for z in ("on_peat_no_fire", "on_peat_fire", "off_peat_no_fire", "off_peat_fire")}
    assert sum(counts.values()) == v["recovery_blocks_west_125"]["value"]
    assert counts["on_peat_no_fire"] == 6 * 3 and counts["on_peat_fire"] == 6 * 3
    assert "recovery_hv_share_regained_on_peat_fire_west_125" in v
