import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('responsive', ROOT / 'scripts/responsive-waybar.py')
responsive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responsive)


class ResponsiveLayoutTests(unittest.TestCase):
    def setUp(self):
        self.shared = responsive.read_jsonc(ROOT / 'config-shared.jsonc')

    def layout(self, width, **options):
        monitor = dict(name='TEST', width=width, height=1440, scale=1, transform=0)
        monitor.update(options)
        return responsive.layouts([monitor], self.shared)[0]

    def test_music_is_first_module_removed(self):
        wide = self.layout(2560)
        narrow = self.layout(1920)
        self.assertIn('group/now-playing', wide['modules-right'])
        self.assertNotIn('group/now-playing', narrow['modules-right'])
        self.assertIn('custom/network', narrow['modules-left'])
        self.assertIn('group/hardware-stats', narrow['modules-right'])
        self.assertNotIn('group/hardware-stats', narrow)

    def test_scaling_and_rotation_use_logical_width(self):
        self.assertNotIn('group/now-playing', self.layout(2560, scale=1.5)['modules-right'])
        self.assertNotIn('group/now-playing', self.layout(2560, transform=3)['modules-right'])
        self.assertIn('custom/network', self.layout(2560, transform=3)['modules-left'])

    def test_breakpoints_and_compact_controls(self):
        self.assertIn('group/now-playing', self.layout(2000)['modules-right'])
        self.assertIn('custom/network', self.layout(1400)['modules-left'])
        self.assertNotIn('custom/network', self.layout(1399)['modules-left'])
        small = self.layout(800)
        self.assertNotIn('custom/weather', small['modules-left'])
        self.assertEqual(len(small['group/hardware-stats']['modules']), 3)
        self.assertIn('custom/quickmenu', small['modules-right'])
        self.assertIn('pulseaudio', small['modules-right'])
        self.assertIn('ext/workspaces', small['modules-left'])

    def test_disabled_outputs_and_stable_order(self):
        monitors = [dict(name=n, width=2560, height=1440, disabled=n == 'off')
                    for n in ('DP-2', 'off', 'DP-1')]
        bars = responsive.layouts(monitors, self.shared)
        self.assertEqual([b['output'] for b in bars], ['DP-1', 'DP-2'])
        self.assertEqual(bars, responsive.layouts(list(reversed(monitors)), self.shared))


if __name__ == '__main__':
    unittest.main()
