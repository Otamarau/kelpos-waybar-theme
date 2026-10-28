#!/usr/bin/env python3
"""Run Waybar with per-output layouts based on Hyprland logical monitor widths."""
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def read_jsonc(path):
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else '',
                  path.read_text(), flags=re.S)
    return json.loads(text)


def logical_width(monitor):
    dimension = 'height' if int(monitor.get('transform', 0)) % 2 else 'width'
    return float(monitor[dimension]) / float(monitor.get('scale', 1))


def layouts(monitors, shared):
    bars = []
    for monitor in sorted(monitors, key=lambda m: m['name']):
        if monitor.get('disabled'):
            continue
        width = logical_width(monitor)
        left = list(shared['modules-left'])
        right = list(shared['modules-right'])
        bar = {'output': monitor['name'], 'include': str(ROOT / 'config-shared.jsonc'),
               'on-sigusr2': 'reload'}
        if width < 2000:
            right = [m for m in right if m != 'group/now-playing']
            left = [m for m in left if m != 'custom/system-spacer-right']
            bar['fixed-center'] = True
        if width < 1400:
            left = [m for m in left if m != 'custom/network']
            bar['spacing'] = 4
        if width < 1100:
            left = [m for m in left if m not in
                    ('custom/weather', 'custom/clipboard', 'custom/screenshot')]
            bar['spacing'] = 2
            # Allow the clock to shift if workspace buttons need more room.
            bar['fixed-center'] = False
        if width < 900:
            bar['group/hardware-stats'] = {
                'orientation': 'horizontal',
                'modules': ['custom/cpu-wheel', 'custom/ram-wheel', 'custom/gpu']}
            left = [m for m in left if m != 'custom/tailscale']
        bar['modules-left'] = left
        bar['modules-right'] = right
        bars.append(bar)
    return bars


def current_layouts():
    result = subprocess.run(['hyprctl', 'monitors', '-j'], capture_output=True,
                            text=True, check=True, timeout=3)
    return layouts(json.loads(result.stdout), read_jsonc(ROOT / 'config-shared.jsonc'))


def write_config(path, bars):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(bars, indent=2) + '\n')
    temporary.replace(path)


def main():
    if '--print-config' in sys.argv:
        print(json.dumps(current_layouts(), indent=2))
        return
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/tmp/waybar-{os.getuid()}')) / 'waybar-responsive'
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = (runtime / 'launcher.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    config = runtime / 'config.json'
    try:
        bars = current_layouts()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Waybar: monitor query failed; using static layout: {error}', file=sys.stderr)
        bars = []
    # An include-only fallback also handles startup before monitors are ready.
    write_config(config, bars or [{'include': str(ROOT / 'config-shared.jsonc')}])
    process = subprocess.Popen(['waybar', '-c', str(config), '-s', str(ROOT / 'style.css')])
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping and process.poll() is None:
            time.sleep(2)
            try:
                updated = current_layouts()
                # Ignore transient empty/error replies during output reconfiguration.
                if updated and updated != bars:
                    write_config(config, updated)
                    bars = updated
                    process.send_signal(signal.SIGUSR2)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                continue
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        lock.close()


if __name__ == '__main__':
    main()
