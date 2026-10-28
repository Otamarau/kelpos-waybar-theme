#!/usr/bin/env python3
"""Compact Waybar temperatures with sensor-specific colour thresholds."""

import argparse
import html
import json
from pathlib import Path
import re


def read_temperature(path):
    return float(path.read_text()) / 1000


def cpu_tooltip(primary, readings, warm, hot):
    label, value, _, _ = primary
    lines = [f'<b>CPU · {value:.1f}°C</b>', html.escape(label)]
    cores = []
    other = []
    for reading in readings:
        name, temp, _, _ = reading
        if reading == primary:
            continue
        core = re.fullmatch(r'Core (\d+)', name)
        if core:
            cores.append((int(core[1]), temp))
        else:
            other.append(f'{name}: {temp:.1f}°C')
    if other:
        lines.extend(['', html.escape('\n'.join(other))])
    if cores:
        cores.sort()
        cells = [f'{number:>2}: {temp:4.1f}°' for number, temp in cores]
        rows = ['   '.join(cells[i:i + 3]) for i in range(0, len(cells), 3)]
        lines.extend(['', '<b>Cores</b>',
                      '<span font_family="monospace" size="small">'
                      + html.escape('\n'.join(rows)) + '</span>'])
    lines.extend(['', f'<small>Amber ≥ {warm:g}°C · Red ≥ {hot:g}°C</small>'])
    return '\n'.join(lines)


def status(component):
    if component == "cpu":
        devices = [p for p in sorted(Path('/sys/class/hwmon').glob('hwmon*'))
                   if (p / 'name').read_text().strip() in ('coretemp', 'k10temp', 'zenpower')]
    else:
        devices = sorted(Path('/sys/class/drm').glob('card[0-9]*/device/hwmon/hwmon*'))
    readings = []
    for device in devices:
        for sensor in sorted(device.glob('temp*_input')):
            prefix = sensor.name.removesuffix('_input')
            label_path = device / (prefix + '_label')
            label = label_path.read_text().strip() if label_path.exists() else prefix
            try:
                readings.append((label, read_temperature(sensor), device, prefix))
            except (OSError, ValueError):
                continue
    if not readings:
        raise ValueError('no temperature sensor available')
    priorities = ['Tdie', 'Tctl', 'Package id 0'] if component == 'cpu' else ['edge', 'temp1']
    primary = next((r for label in priorities for r in readings if r[0] == label), readings[0])
    label, value, device, prefix = primary
    # Display cues, not hardware limits: warn before the sensor's critical point.
    critical = 100.0
    high = None
    for suffix in ('crit', 'max'):
        try:
            limit = read_temperature(device / (prefix + '_' + suffix))
            if 40 <= limit <= 150:
                if suffix == 'crit':
                    critical = limit
                else:
                    high = limit
        except (OSError, ValueError):
            pass
    hot = critical - 10
    warm = min(high if high is not None else critical - 20, hot - 5)
    state = 'hot' if value >= hot else 'warm' if value >= warm else 'cool'
    tooltip = [f'{component.upper()}: {value:.1f}°C ({label})']
    tooltip += [f'{name}: {temp:.1f}°C' for name, temp, _, _ in readings]
    tooltip += [f'Amber ≥ {warm:g}°C · Red ≥ {hot:g}°C']
    markup = cpu_tooltip(primary, readings, warm, hot) if component == 'cpu' else html.escape('\n'.join(tooltip))
    return {'text': f'{int(value)}°', 'tooltip': markup, 'class': state}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=('cpu', 'gpu'))
    args = parser.parse_args()
    try:
        result = status(args.component)
    except (OSError, ValueError) as error:
        result = {'text': '—', 'tooltip': html.escape(f'{args.component.upper()}: {error}'), 'class': 'unavailable'}
    print(json.dumps(result))
