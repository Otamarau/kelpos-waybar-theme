#!/usr/bin/env python3
"""NetworkManager Wi-Fi list embedded in Rofi's Quick Menu."""
import base64
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unicodedata
import uuid
import gi
gi.require_version('NM', '1.0')
from gi.repository import GLib, NM

SEC = getattr(NM, '80211ApSecurityFlags')
AP_FLAGS = getattr(NM, '80211ApFlags')


def clean(text):
    return ''.join(c if c.isprintable() or unicodedata.category(c) == 'Co' else ' '
                   for c in str(text))


def encode(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode(data):
    return json.loads(base64.urlsafe_b64decode(data))


def header(key, value):
    print(f'\0{key}\x1f{value}')


def row(label, action, **options):
    fields = ['info', encode(action)]
    for key, value in options.items():
        fields.extend([key, str(value)])
    print(clean(label) + '\0' + '\x1f'.join(fields))


def notify(message):
    subprocess.run(['notify-send', 'Wi-Fi', clean(message)], check=False)


def refresh_notification(message, notification_id=None, finished=False):
    args = ['notify-send', '--print-id', '--transient', '--app-name', 'Quick Menu',
            '--expire-time', '2000' if finished else '15000']
    if notification_id:
        args += ['--replace-id', notification_id]
    try:
        result = subprocess.run(args + ['Wi-Fi', message], capture_output=True,
                                text=True, timeout=2)
        value = result.stdout.strip()
        return value if result.returncode == 0 and value.isdigit() else None
    except (OSError, subprocess.SubprocessError):
        return None  # Notifications must never prevent refreshing the menu.


def detached(arguments):
    # Rofi waits for inherited output pipes, so detach all descriptors.
    subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def security(ap):
    flags = ap.get_rsn_flags() | ap.get_wpa_flags()
    if flags & SEC.KEY_MGMT_802_1X:
        return 'Enterprise', None
    if flags & SEC.KEY_MGMT_PSK:
        return 'WPA', 'wpa-psk'
    if flags & SEC.KEY_MGMT_SAE:
        return 'WPA3', 'sae'
    if flags & SEC.KEY_MGMT_OWE:
        return 'Enhanced open', 'owe'
    if ap.get_flags() & AP_FLAGS.PRIVACY:
        return 'WEP / advanced', None
    return 'Open', ''


def wifi_devices(client):
    return [d for d in client.get_devices() if d.get_device_type() == NM.DeviceType.WIFI]


def networks(client):
    choices = {}
    for device in wifi_devices(client):
        current = device.get_active_access_point()
        for ap in device.get_access_points():
            ssid = ap.get_ssid()
            if ssid is None or not ssid.get_data():
                continue
            raw = bytes(ssid.get_data())
            label, key_mgmt = security(ap)
            item = {'name': clean(NM.utils_ssid_to_utf8(raw)), 'interface': device.get_iface(),
                    'bssid': ap.get_bssid(), 'strength': ap.get_strength(),
                    'connected': current is not None and current.get_path() == ap.get_path(),
                    'security': label, 'key_mgmt': key_mgmt}
            key = (raw, label, device.get_iface())
            prior = choices.get(key)
            if prior is None or (item['connected'], item['strength']) > (prior['connected'], prior['strength']):
                choices[key] = item
    return sorted(choices.values(), key=lambda n: (not n['connected'], -n['strength'], n['name'].casefold()))


def show(client, message=''):
    header('no-custom', 'true')
    header('markup-rows', 'false')
    header('prompt', '󰤨')
    if not client.get_nm_running():
        header('message', 'NetworkManager is not running.')
        row('Open Connection Editor', {'action': 'editor'})
        return
    devices = wifi_devices(client)
    wired = [d for d in client.get_devices() if d.get_device_type() == NM.DeviceType.ETHERNET]
    connected_wired = [d for d in wired if d.get_state() == NM.DeviceState.ACTIVATED]
    enabled = client.wireless_get_enabled()
    summary = 'Wi-Fi on · select a network to connect' if enabled else 'Wi-Fi off'
    if not devices:
        summary = ('Connected via Ethernet · ' + ', '.join(d.get_iface() for d in connected_wired)
                   if connected_wired else 'No Wi-Fi adapter available · use Connection Editor for wired settings')
    elif not client.wireless_hardware_get_enabled():
        summary = 'Wi-Fi is blocked by a hardware switch.'
    header('message', html.escape(message or summary))
    for device in sorted(wired, key=lambda d: d.get_state() != NM.DeviceState.ACTIVATED):
        active = device.get_active_connection()
        connected = device.get_state() == NM.DeviceState.ACTIVATED
        label = clean(active.get_id()) if active else device.get_iface()
        state = '✓ Connected' if connected else 'Unavailable' if device.get_state() == NM.DeviceState.UNAVAILABLE else 'Disconnected'
        row(f'󰈀  {label} · {device.get_iface()}   {state}', {'action': 'editor'},
            active='true' if connected else 'false', meta='Ethernet wired settings')
    if enabled:
        entries = networks(client)
        for item in entries:
            strength = item['strength']
            icon = '󰤨' if strength >= 75 else '󰤥' if strength >= 50 else '󰤢' if strength >= 25 else '󰤟'
            state = '✓ Connected' if item['connected'] else '󰌾' if item['security'] != 'Open' else 'open'
            row(f'{icon}  {item["name"]}   {strength:>3}%   {state}',
                dict(item, action='current' if item['connected'] else 'connect'),
                active='true' if item['connected'] else 'false',
                meta=f'{item["interface"]} {item["security"]}')
        if not entries and devices:
            row('No networks found — select Refresh', {'action': 'refresh'}, nonselectable='true')
        for device in devices:
            if device.get_active_access_point():
                row(f'Disconnect · {device.get_iface()}', {'action': 'disconnect', 'interface': device.get_iface()})
    if devices:
        row('󰑐  Refresh networks', {'action': 'refresh'})
        row('Turn Wi-Fi off' if enabled else 'Turn Wi-Fi on', {'action': 'radio', 'enabled': not enabled})
    row('Hidden / advanced network…' if devices else 'Open full network menu…', {'action': 'advanced'})
    row('Open Connection Editor', {'action': 'editor'})


def connect(item):
    time.sleep(0.25)  # Let the old Rofi window release its keyboard grab.
    client = NM.Client.new(None)
    device = next((d for d in wifi_devices(client) if d.get_iface() == item['interface']), None)
    ap = next((a for a in device.get_access_points() if a.get_bssid() == item['bssid']), None) if device else None
    if ap is None:
        notify('Network is no longer available. Refresh the list and try again.')
        return
    profiles = [c for c in device.filter_connections(client.get_connections()) if ap.connection_valid(c)]
    profile = max(profiles, key=lambda c: c.get_setting_connection().get_timestamp()) if profiles else None
    if profile is None:
        label, key_mgmt = security(ap)
        if key_mgmt is None:
            notify(f'{label} requires advanced setup. Opening the network menu.')
            detached(['networkmanager_dmenu'])
            return
        password = None
        if key_mgmt in ('wpa-psk', 'sae'):
            result = subprocess.run(['rofi', '-dmenu', '-password', '-no-history', '-p', 'Wi-Fi password',
                                     '-mesg', html.escape(item['name'])], input='', capture_output=True, text=True)
            if result.returncode != 0 or not result.stdout.rstrip('\n'):
                return
            password = result.stdout.rstrip('\n')
        profile = NM.SimpleConnection.new()
        setting = NM.SettingConnection.new()
        setting.props.id = NM.utils_ssid_to_utf8(bytes(ap.get_ssid().get_data()))
        setting.props.uuid = str(uuid.uuid4())
        setting.props.type = '802-11-wireless'
        profile.add_setting(setting)
        wireless = NM.SettingWireless.new()
        wireless.props.ssid = ap.get_ssid()
        wireless.props.mode = 'infrastructure'
        profile.add_setting(wireless)
        if key_mgmt:
            secure = NM.SettingWirelessSecurity.new()
            secure.props.key_mgmt = key_mgmt
            if password is not None:
                secure.props.psk = password
            profile.add_setting(secure)
    notify(f'Connecting to {item["name"]}…')
    loop = GLib.MainLoop()
    outcome = {'message': f'Connection to {item["name"]} timed out.'}

    def check_state(active, *_):
        state = active.get_state()
        if state == NM.ActiveConnectionState.ACTIVATED:
            outcome['message'] = f'Connected to {item["name"]}'
            loop.quit()
        elif state == NM.ActiveConnectionState.DEACTIVATED:
            outcome['message'] = f'Could not connect to {item["name"]}. Check the password or use Connection Editor.'
            loop.quit()

    def ready(client, result, *_):
        try:
            active = (client.activate_connection_finish(result) if profiles
                      else client.add_and_activate_connection_finish(result))
            active.connect('notify::state', check_state)
            check_state(active)
        except GLib.Error as error:
            outcome['message'] = f'Connection failed: {error.message}'
            loop.quit()

    if profiles:
        client.activate_connection_async(profile, device, ap.get_path(), None, ready, None)
    else:
        client.add_and_activate_connection_async(profile, device, ap.get_path(), None, ready, None)
    GLib.timeout_add_seconds(45, lambda: (loop.quit(), False)[1])
    loop.run()
    notify(outcome['message'])


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--connect':
        connect(decode(sys.argv[2]))
        return
    message = ''
    if os.environ.get('ROFI_RETV', '0') == '1':
        item = decode(os.environ.get('ROFI_INFO', ''))
        action = item['action']
        if action == 'connect':
            detached([sys.executable, str(Path(__file__).resolve()), '--connect', encode(item)])
            return
        if action in ('editor', 'advanced'):
            program = 'nm-connection-editor' if action == 'editor' else 'networkmanager_dmenu'
            detached(['sh', '-c', 'sleep 0.25; exec "$1"', 'wifi-menu', program])
            return
        if action in ('radio', 'refresh', 'disconnect'):
            args = (['radio', 'wifi', 'on' if item['enabled'] else 'off'] if action == 'radio'
                    else ['device', 'wifi', 'list', '--rescan', 'yes'] if action == 'refresh'
                    else ['device', 'disconnect', item['interface']])
            notification_id = refresh_notification('Refreshing networks…') if action == 'refresh' else None
            try:
                result = subprocess.run(['nmcli', '--wait', '8', *args], capture_output=True, text=True, timeout=12)
                message = ('Network list refreshed.' if action == 'refresh'
                           else 'Wi-Fi updated.') if result.returncode == 0 else clean(result.stderr.strip())
            except (OSError, subprocess.SubprocessError):
                if action == 'refresh':
                    refresh_notification('Could not refresh networks.', notification_id, finished=True)
                raise
            if action == 'refresh':
                refresh_notification('Networks refreshed.' if result.returncode == 0
                                     else 'Could not refresh networks.', notification_id, finished=True)
    show(NM.Client.new(None), message)


if __name__ == '__main__':
    try:
        main()
    except (GLib.Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        if '--connect' in sys.argv:
            notify(f'Connection failed: {error}')
        else:
            header('no-custom', 'true')
            header('message', html.escape(f'Wi-Fi unavailable: {clean(error)}'))
            row('Open Connection Editor', {'action': 'editor'})
