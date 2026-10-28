#!/usr/bin/env python3
"""Fixed-width download/upload rates for the default network interface."""

import html
import json
from pathlib import Path
import subprocess
import time


def ip_json(*arguments):
    result = subprocess.run(['ip', '-j', *arguments], capture_output=True, text=True,
                            check=True, timeout=3)
    return json.loads(result.stdout)


def connection():
    routes = ip_json('-4', 'route', 'show', 'default')
    if not routes:
        routes = ip_json('-6', 'route', 'show', 'default')
    routes = [r for r in routes if r.get('dev') and 'linkdown' not in r.get('flags', [])]
    if not routes:
        return None, []
    route = min(routes, key=lambda r: r.get('metric', 0))
    interface = route['dev']
    addresses = [a['local'] for entry in ip_json('address', 'show', 'dev', interface)
                 for a in entry.get('addr_info', []) if a.get('scope') == 'global']
    return interface, addresses


def counters(interface):
    for line in Path('/proc/net/dev').read_text().splitlines()[2:]:
        name, values = line.split(':', 1)
        if name.strip() == interface:
            fields = values.split()
            return int(fields[0]), int(fields[8])
    raise ValueError('interface disappeared')


def rate_text(rate):
    # Decimal units, as labelled: KB = 1000 bytes. Every field is ten characters.
    value = max(0, rate)
    units = ('B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s')
    for unit in units:
        if value < 999.5 or unit == units[-1]:
            break
        value /= 1000
    number = f'{value:.0f}' if value >= 100 or unit == 'B/s' else f'{value:.1f}'
    # Put spare space after the reading, not between the arrow and number.
    return f'{number} {unit}'.ljust(10)


def display(interface, addresses, down, up):
    return {
        'text': f'↓ {rate_text(down)}  ↑ {rate_text(up)}',
        'tooltip': html.escape(f'Interface: {interface}\nIP: {", ".join(addresses) or "—"}'
                              f'\nDownload: {rate_text(down).strip()}'
                              f'\nUpload: {rate_text(up).strip()}'),
        'class': 'idle' if max(down, up) < 1024 else 'active',
    }


def main():
    interface, addresses = None, []
    previous = None
    next_connection = 0
    while True:
        try:
            now = time.monotonic()
            if now >= next_connection:
                selected, addresses = connection()
                if selected != interface:
                    previous = None
                interface = selected
                next_connection = now + 5
            if interface is None:
                result = {'text': '↓     —       ↑     —',
                          'tooltip': 'Network disconnected: no default route', 'class': 'disconnected'}
            else:
                rx, tx = counters(interface)
                sampled = time.monotonic()
                down = up = 0
                if previous is not None:
                    old_rx, old_tx, old_time = previous
                    elapsed = sampled - old_time
                    if elapsed > 0:
                        down = max(0, rx - old_rx) / elapsed
                        up = max(0, tx - old_tx) / elapsed
                previous = rx, tx, sampled
                result = display(interface, addresses, down, up)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            previous = None
            next_connection = 0
            result = {'text': '↓     —       ↑     —',
                      'tooltip': html.escape(f'Network unavailable: {error}'), 'class': 'disconnected'}
        print(json.dumps(result), flush=True)
        time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass
