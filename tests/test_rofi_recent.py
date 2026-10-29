import json
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class RecentAppsTests(unittest.TestCase):
    def test_launch_order_and_deduplication(self):
        recorder = runpy.run_path(str(ROOT / "bin/rofi-record-launch"))
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_STATE_HOME": directory}):
                for app in ("dolphin.desktop", "files.desktop", "dolphin.desktop"):
                    recorder["record"](app)
            history = json.loads((Path(directory) / "rofi/recent-apps.json").read_text())
            self.assertEqual(history, ["dolphin.desktop", "files.desktop"])

    def test_launcher_applies_recorded_order_and_search_options(self):
        launcher = runpy.run_path(str(ROOT / "bin/rofi-recent"))
        recorder = runpy.run_path(str(ROOT / "bin/rofi-record-launch"))
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            cache.mkdir()
            history = cache / "rofi3.druncache"
            history.write_text("100 dolphin.desktop\n1 files.desktop\n")
            environment = {"XDG_CACHE_HOME": str(cache), "XDG_STATE_HOME": str(Path(directory) / "state")}

            def fake_rofi(command):
                self.assertIn("-sort", command)
                index = command.index("-drun-DBusActivatable")
                self.assertEqual(command[index + 1], "false")
                self.assertIn("rofi-record-launch", command[command.index("-run-command") + 1])
                recorder["record"]("files.desktop")
                return SimpleNamespace(returncode=0)

            with patch.dict(os.environ, environment), patch("sys.argv", ["rofi-recent"]):
                with patch("subprocess.run", fake_rofi):
                    self.assertEqual(launcher["main"](), 0)
                self.assertEqual(list(launcher["read_history"](history)), ["files.desktop", "dolphin.desktop"])
                with patch("subprocess.run", return_value=SimpleNamespace(returncode=1)):
                    self.assertEqual(launcher["main"](), 1)
                self.assertEqual(list(launcher["read_history"](history)), ["files.desktop", "dolphin.desktop"])


if __name__ == "__main__":
    unittest.main()
