import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('wifi', Path(__file__).resolve().parents[1] / 'scripts/wifi-menu.py')
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)


def access_point(name, strength, path, flags=0, private=False):
    ap = Mock()
    ap.get_ssid.return_value = wifi.GLib.Bytes.new(name.encode())
    ap.get_strength.return_value = strength
    ap.get_path.return_value = path
    ap.get_bssid.return_value = path
    ap.get_rsn_flags.return_value = flags
    ap.get_wpa_flags.return_value = 0
    ap.get_flags.return_value = wifi.AP_FLAGS.PRIVACY if private else 0
    ap.connection_valid.return_value = True
    return ap


class WifiMenuTests(unittest.TestCase):
    def setUp(self):
        self.ap = access_point('Home', 60, '/ap/1', wifi.SEC.KEY_MGMT_PSK)
        self.device = Mock()
        self.device.get_iface.return_value = 'wlan0'
        self.device.get_access_points.return_value = [self.ap]
        self.device.get_active_access_point.return_value = self.ap
        self.device.filter_connections.return_value = []
        self.client = Mock()
        self.client.get_devices.return_value = []
        self.client.get_nm_running.return_value = True
        self.client.wireless_get_enabled.return_value = True
        self.client.wireless_hardware_get_enabled.return_value = True
        self.item = {'name': 'Home', 'interface': 'wlan0', 'bssid': '/ap/1'}

    def test_connected_first_and_duplicate_ap_collapse(self):
        self.device.get_access_points.return_value = [
            access_point('Home', 99, '/ap/2', wifi.SEC.KEY_MGMT_PSK),
            access_point('Cafe', 90, '/ap/3'), self.ap,
            access_point('Other', 20, '/ap/4')]
        with patch.object(wifi, 'wifi_devices', return_value=[self.device]):
            entries = wifi.networks(self.client)
        self.assertEqual([n['name'] for n in entries], ['Home', 'Cafe', 'Other'])
        self.assertEqual(entries[0]['bssid'], '/ap/1')

    def test_security_classification(self):
        for flags, private, expected in [
            (0, False, ''), (0, True, None),
            (wifi.SEC.KEY_MGMT_PSK, True, 'wpa-psk'),
            (wifi.SEC.KEY_MGMT_SAE, True, 'sae'),
            (wifi.SEC.KEY_MGMT_802_1X, True, None),
            (wifi.SEC.KEY_MGMT_OWE, True, 'owe')]:
            self.assertEqual(wifi.security(access_point('X', 50, '/x', flags, private))[1], expected)

    def test_names_cannot_inject_rofi_rows(self):
        out = io.StringIO()
        data = {'name': 'Cafe\n\0<&>:$HOME', 'action': 'connect'}
        with contextlib.redirect_stdout(out):
            wifi.row(data['name'], data)
        lines = out.getvalue().split('\n')
        self.assertEqual(len(lines), 2)
        self.assertEqual(out.getvalue().count('\0'), 1)
        self.assertEqual(wifi.decode(lines[0].split('\x1f')[1]), data)

    def test_menu_and_radio_off(self):
        for enabled in [True, False]:
            self.client.wireless_get_enabled.return_value = enabled
            out = io.StringIO()
            with patch.object(wifi, 'wifi_devices', return_value=[self.device]), contextlib.redirect_stdout(out):
                wifi.show(self.client)
            text = out.getvalue()
            self.assertIn('Open Connection Editor', text)
            self.assertIn('Refresh networks', text)
            self.assertEqual('✓ Connected' in text, enabled)
            self.assertIn('Turn Wi-Fi off' if enabled else 'Turn Wi-Fi on', text)

    def test_password_cancel_does_not_connect(self):
        with patch.object(wifi.NM.Client, 'new', return_value=self.client), \
             patch.object(wifi, 'wifi_devices', return_value=[self.device]), \
             patch.object(wifi.time, 'sleep'), \
             patch.object(wifi.subprocess, 'run', return_value=Mock(returncode=1, stdout='')):
            wifi.connect(self.item)
        self.client.add_and_activate_connection_async.assert_not_called()
        self.client.activate_connection_async.assert_not_called()

    def test_ethernet_only_system_shows_connection_and_icon(self):
        ethernet = Mock()
        ethernet.get_device_type.return_value = wifi.NM.DeviceType.ETHERNET
        ethernet.get_state.return_value = wifi.NM.DeviceState.ACTIVATED
        ethernet.get_iface.return_value = 'enp7s0'
        ethernet.get_active_connection.return_value.get_id.return_value = 'Wired connection'
        self.client.get_devices.return_value = [ethernet]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            wifi.show(self.client)
        text = out.getvalue()
        self.assertIn('\0prompt\x1f󰤨', text)
        self.assertIn('Connected via Ethernet · enp7s0', text)
        self.assertIn('Wired connection · enp7s0', text)
        self.assertIn('󰈀', text)
        self.assertIn('Open full network menu', text)
        self.assertNotIn('Turn Wi-Fi', text)

    def test_new_password_is_passed_to_libnm_not_command_line(self):
        with patch.object(wifi.NM.Client, 'new', return_value=self.client), \
             patch.object(wifi, 'wifi_devices', return_value=[self.device]), \
             patch.object(wifi.time, 'sleep'), patch.object(wifi, 'notify'), \
             patch.object(wifi.GLib, 'MainLoop'), patch.object(wifi.GLib, 'timeout_add_seconds'), \
             patch.object(wifi.subprocess, 'run', return_value=Mock(returncode=0, stdout='test-passphrase\n')) as run:
            wifi.connect(self.item)
        profile = self.client.add_and_activate_connection_async.call_args.args[0]
        self.assertEqual(profile.get_setting_wireless_security().props.psk, 'test-passphrase')
        self.assertNotIn('test-passphrase', str(run.call_args))
        self.assertEqual(bytes(profile.get_setting_wireless().get_ssid().get_data()), b'Home')

    def test_saved_profile_reused_without_password_prompt(self):
        profile = Mock()
        profile.get_setting_connection.return_value.get_timestamp.return_value = 1
        self.device.filter_connections.return_value = [profile]
        with patch.object(wifi.NM.Client, 'new', return_value=self.client), \
             patch.object(wifi, 'wifi_devices', return_value=[self.device]), \
             patch.object(wifi.time, 'sleep'), patch.object(wifi, 'notify'), \
             patch.object(wifi.GLib, 'MainLoop'), patch.object(wifi.GLib, 'timeout_add_seconds'), \
             patch.object(wifi.subprocess, 'run') as run:
            wifi.connect(self.item)
        run.assert_not_called()
        self.client.activate_connection_async.assert_called_once()
        self.client.add_and_activate_connection_async.assert_not_called()

    def test_activation_feedback_follows_actual_state(self):
        profile = Mock()
        profile.get_setting_connection.return_value.get_timestamp.return_value = 1
        self.device.filter_connections.return_value = [profile]
        for state, expected in [(wifi.NM.ActiveConnectionState.ACTIVATED, 'Connected to Home'),
                                (wifi.NM.ActiveConnectionState.DEACTIVATED, 'Could not connect to Home')]:
            active = Mock()
            active.get_state.return_value = state
            self.client.activate_connection_finish.return_value = active
            loop = Mock()
            def complete():
                callback = self.client.activate_connection_async.call_args.args[4]
                callback(self.client, Mock())
            loop.run.side_effect = complete
            with patch.object(wifi.NM.Client, 'new', return_value=self.client), \
                 patch.object(wifi, 'wifi_devices', return_value=[self.device]), \
                 patch.object(wifi.time, 'sleep'), patch.object(wifi, 'notify') as notify, \
                 patch.object(wifi.GLib, 'MainLoop', return_value=loop), \
                 patch.object(wifi.GLib, 'timeout_add_seconds'):
                wifi.connect(self.item)
            self.assertIn(expected, notify.call_args.args[0])
            loop.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
