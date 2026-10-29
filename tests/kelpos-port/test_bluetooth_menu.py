"""Exercise Rofi callbacks with a fake bluetoothctl; never touch real radios."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/quick-controls-bluetooth.sh'
MAC = 'AA:BB:CC:DD:EE:FF'


class BluetoothMenuTests(unittest.TestCase):
    def run_menu(self, selection='', **settings):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / 'bluetoothctl'
            fake.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
args = sys.argv[1:]
assert '--timeout' not in args, 'bluetoothctl internal timeout delays menu queries'
with open(os.environ['BT_LOG'], 'a') as log:
    log.write(' '.join(args) + '\\n')
command = args[0]
state = Path(os.environ['BT_STATE'])
connected = state.exists() if os.environ.get('CONNECTED') != 'yes' else not state.exists()
if command == 'show':
    if os.environ.get('UNAVAILABLE'): sys.exit(1)
    print('Controller AA:BB:CC:DD:EE:00\\n\\tPowered: ' + os.environ.get('POWERED', 'yes'))
elif command == 'devices':
    if os.environ.get('DEVICES_FAIL'): sys.exit(1)
    print('Device AA:BB:CC:DD:EE:FF Test headphones')
elif command == 'info':
    print('Device AA:BB:CC:DD:EE:FF\\n\\tConnected: ' + ('yes' if connected else 'no'))
elif command in ('connect', 'disconnect', 'power'):
    if os.environ.get('FAIL'): sys.exit(1)
    state.touch()
''')
            fake.chmod(0o755)
            notifier = root / 'notify-send'
            notifier.write_text("#!/bin/sh\nprintf 'notify %s\\n' \"$*\" >> \"$BT_LOG\"\necho 42\n")
            notifier.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:' + os.environ['PATH'],
                       ROFI_RETV='1' if selection else '0',
                       BT_LOG=str(root / 'log'), BT_STATE=str(root / 'state'), **settings)
            result = subprocess.run(['bash', str(SCRIPT), selection], env=env,
                                    capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            return result.stdout.decode(), (root / 'log').read_text()

    def test_refresh_returns_rows_and_preserves_filter(self):
        output, _ = self.run_menu('Refresh')
        self.assertIn('Test headphones', output)
        _, log = self.run_menu('Refresh')
        self.assertIn('Refreshing Bluetooth devices…', log)
        self.assertIn('--replace-id 42', log)
        self.assertIn('Bluetooth devices refreshed.', log)
        self.assertLess(log.index('Refreshing Bluetooth'), log.index('show\n'))
        self.assertIn('\0keep-filter\x1ftrue', output)
        self.assertIn('\0keep-selection\x1ftrue', output)

    def test_indented_connected_status_disconnects_and_redraws(self):
        output, log = self.run_menu(f'● Test headphones [{MAC}]', CONNECTED='yes')
        self.assertIn(f'disconnect {MAC}\n', log)
        self.assertNotIn(f'\nconnect {MAC}\n', log)
        self.assertIn('○ Test headphones', output)
        self.assertIn('Device disconnected.', output)

    def test_connect_redraws_updated_status(self):
        output, log = self.run_menu(f'○ Test headphones [{MAC}]')
        self.assertIn(f'connect {MAC}\n', log)
        self.assertIn('● Test headphones', output)

    def test_connection_failure_stays_open_without_repairing(self):
        output, log = self.run_menu(f'○ Test headphones [{MAC}]', FAIL='yes')
        self.assertIn('Could not connect.', output)
        self.assertIn('Refresh\n', output)
        self.assertNotIn('pair ', log)
        self.assertNotIn('trust ', log)

    def test_power_failure_stays_open(self):
        output, _ = self.run_menu('Enable Bluetooth', POWERED='no', FAIL='yes')
        self.assertIn('Could not enable Bluetooth.', output)
        self.assertIn('Enable Bluetooth\n', output)

    def test_unavailable_adapter_stays_open(self):
        output, _ = self.run_menu('Refresh', UNAVAILABLE='yes')
        self.assertIn('Bluetooth unavailable.', output)
        self.assertIn('Refresh\n', output)

    def test_device_query_failure_stays_open(self):
        output, _ = self.run_menu('Refresh', DEVICES_FAIL='yes')
        self.assertIn('Could not read Bluetooth devices.', output)
        self.assertIn('Refresh\n', output)


if __name__ == '__main__':
    unittest.main()

