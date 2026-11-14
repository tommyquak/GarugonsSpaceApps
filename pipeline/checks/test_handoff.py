# Written with Super Intelligence (SI) assistance.
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.checks.run import persist


class HandoffTest(unittest.TestCase):
    def test_first_qualifying_rain_requires_complete_consecutive_days_and_source_agreement(self):
        from datetime import date, timedelta
        from pipeline.checks.run import released_onset
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            start = date(2026, 5, 1)
            days = [(start + timedelta(days=i)).isoformat() for i in range(65)]
            daily = dict.fromkeys(days, 0)
            daily[days[37]] = 6  # isolated wet day, followed by <25 mm in five days
            for day in days[51:56]:
                daily[day] = 5
            path = root / "rain_daily_west.json"
            path.write_text(json.dumps(daily))
            upstream = {"last_dry_day_west": {"made_by": "pipeline/season.py", "value": days[50]}}
            self.assertEqual(released_onset(root, "west", upstream), days[51])
            upstream["last_dry_day_west"]["value"] = days[36]
            with self.assertRaisesRegex(ValueError, "do not reproduce"):
                released_onset(root, "west", upstream)
            del daily[days[49]]
            path.write_text(json.dumps(daily))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                released_onset(root, "west", upstream)

    def test_verified_results_keep_other_tracks_and_gate_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            output, seed = Path(td) / "validation.json", Path(td) / "upstream.json"
            seed.write_text(json.dumps({"another_track": {"value": 42, "status": "exploratory"}}))
            row = dict(value=.456789, unit="dB", site="west", made_by="pipeline/checks/two_orbit.py", note="unit test")
            a, b = "track5_west_orbit", "track5_west_rebound"
            entries = {a: row, b: {**row, "made_by": "pipeline/checks/recovery.py"}}
            args = (output, seed, ["orbit", "recovery"], entries, {b})
            persist(*args, False)
            persist(*args, True)
            saved = output.read_bytes()
            rows = json.loads(saved)
            self.assertEqual(rows[a]["status"], "final")
            self.assertEqual(rows[b]["status"], "exploratory")
            self.assertEqual(rows["another_track"], json.loads(seed.read_text())["another_track"])
            entries[a] = {**row, "value": .5}
            with self.assertRaisesRegex(ValueError, "changed"):
                persist(*args, True)
            self.assertEqual(output.read_bytes(), saved)

    def test_disappearing_input_does_not_erase_verified_result(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "validation.json"
            row = dict(value=.3, unit="share", site="west", note="", made_by="pipeline/checks/peat_split.py")
            persist(path, None, ["peat"], {"track5_west_peat": row}, set(), False)
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "coverage changed"):
                persist(path, None, ["peat"], {}, set(), True)
            self.assertEqual(path.read_bytes(), before)

    def test_repeat_refuses_subprecision_drift_without_overwriting_handoff(self):
        from unittest.mock import patch
        from pipeline.checks.run import main
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "validation.json"
            before = b'{"previous_handoff": {"value": 42}}\n'
            path.write_bytes(before)
            key = "track5_west_orbit"
            row = dict(value=.456781, unit="share", site="west", note="",
                       made_by="pipeline/checks/two_orbit.py")
            results = [({key: row}, set(), []), ({key: {**row, "value": .456782}}, set(), [])]
            with patch("sys.argv", ["run", "--check", "orbit", "--repeat", "--output", str(path)]), \
                 patch("pipeline.checks.run.make_entries", side_effect=results), \
                 self.assertRaisesRegex(ValueError, "runs differ"):
                main()
            self.assertEqual(path.read_bytes(), before)

    def test_mismatched_forest_reference_stays_exploratory(self):
        from argparse import Namespace
        from unittest.mock import patch
        from pipeline.checks.run import make_entries
        args = Namespace(check=["forest"], layers=Path("."), onsets={})
        with patch("pipeline.checks.forest.calculate", return_value={"forest_p05": (-.3, "dB", "")}):
            entries, held, pending = make_entries(args, {
                "noise_floor_hh_125": {"value": -.2}, "noise_floor_hh_061": {"value": -.3005}})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "validation.json"
            for verify in False, True:
                persist(path, None, ["forest"], entries, held, verify)
            rows = json.loads(path.read_text())
            self.assertEqual(rows["track5_west_125_forest_p05"]["status"], "exploratory")
            self.assertEqual(rows["track5_west_061_forest_p05"]["status"], "final")
            self.assertIn("noise_floor_hh_125", pending[0])

    def test_no_post_cutoff_pass_cannot_reuse_recovery_files_from_an_old_run(self):
        from argparse import Namespace
        from types import SimpleNamespace
        from unittest.mock import patch
        import numpy as np
        from pipeline.checks.run import make_entries
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for site in ("west", "east"):
                for track in ("125", "061"):
                    np.savez(root / f"{site}_{track}.npz", dates=np.array(["20261016"]))
                    for pol in ("hh", "hv"):
                        (root / f"recovery_{pol}_{site}_{track}.tif").touch()
            args = Namespace(check=["recovery"], layers=root, stacks=root, recovery_layers=None, onsets={})
            with patch("pipeline.checks.run.rasterio.open") as op:
                op.return_value.__enter__.return_value = SimpleNamespace(tags=lambda: {"dry_until": "20261025"})
                entries, _, pending = make_entries(args, {})
            self.assertFalse(entries)
            self.assertEqual(sum("no pass after" in reason for reason in pending), 4)
