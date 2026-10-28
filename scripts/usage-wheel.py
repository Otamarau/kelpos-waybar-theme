#!/usr/bin/env python3
"""Stream Waybar JSON for a usage ring; exact readings stay in its tooltip."""

import argparse
import json
from pathlib import Path
import time


# CPU uses a centred SVG overlay; a nonbreaking space keeps its label visible.
ICONS = {"cpu": "\u00a0", "ram": "", "gpu": "󰢮", "vram": "󰘚", "swap": "󰁪"}


def cpu_ticks():
    samples = {}
    for line in Path('/proc/stat').read_text().splitlines():
        fields = line.split()
        name = fields[0]
        if name != 'cpu' and not (name.startswith('cpu') and name[3:].isdigit()):
            continue
        values = [int(v) for v in fields[1:]]
        # Guest time is already included in user/nice; iowait counts as idle.
        samples[name] = (sum(values[:8]), values[3] + values[4])
    return samples


def cpu_usage(current, previous):
    if previous is None:
        return None
    elapsed = current[0] - previous[0]
    if elapsed <= 0:
        return None
    return max(0, min(100, 100 * (1 - (current[1] - previous[1]) / elapsed)))


def cpu_tooltip(percent, current, previous):
    cells = []
    for name in sorted((name for name in current if name != 'cpu'), key=lambda name: int(name[3:])):
        usage = cpu_usage(current[name], previous.get(name))
        value = f'{usage:5.1f}%' if usage is not None else '     —'
        cells.append(f'{int(name[3:]):>2}: {value}')
    rows = ['   '.join(cells[i:i + 4]) for i in range(0, len(cells), 4)]
    return (f'<b>CPU · {percent:.1f}% overall</b>\n\n'
            '<b>Logical CPUs (threads)</b>\n'
            '<span font_family="monospace" size="small">'
            + '\n'.join(rows) + '</span>')


def reading(metric, previous):
    if metric == "cpu":
        current = cpu_ticks()
        percent = cpu_usage(current['cpu'], previous.get('cpu'))
        percent = percent if percent is not None else 0
        return percent, cpu_tooltip(percent, current, previous), current
    if metric in ("ram", "swap"):
        mem = {line.split(':')[0]: int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
        if metric == "swap":
            total = mem['SwapTotal'] * 1024
            used = (mem['SwapTotal'] - mem['SwapFree']) * 1024
            if total == 0:
                return 0, "Swap: disabled", previous
        else:
            total = mem['MemTotal'] * 1024
            used = (mem['MemTotal'] - mem['MemAvailable']) * 1024
    else:
        # Select an actual GPU with VRAM counters, skipping DRM connector entries.
        devices = sorted(Path('/sys/class/drm').glob('card[0-9]*/device'))
        device = next(d for d in devices if (d / 'mem_info_vram_total').exists())
        if metric == 'gpu':
            percent = float((device / 'gpu_busy_percent').read_text())
            return percent, f"GPU: {percent:.1f}%", previous
        used = int((device / 'mem_info_vram_used').read_text())
        total = int((device / 'mem_info_vram_total').read_text())
    percent = used / total * 100
    return percent, f"{metric.upper()}: {used / 2**30:.2f} / {total / 2**30:.2f} GiB ({percent:.1f}%)", previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metric', choices=ICONS)
    parser.add_argument('--once', action='store_true', help='Print one sample for verification')
    args = parser.parse_args()
    previous = cpu_ticks() if args.metric == 'cpu' else None
    if args.metric == 'cpu':
        time.sleep(0.2)
    while True:
        try:
            percent, tooltip, previous = reading(args.metric, previous)
            level = max(0, min(100, round(percent)))
            result = {'text': ICONS[args.metric], 'tooltip': tooltip, 'class': ['usage-wheel', f'level-{level}'], 'percentage': level}
        except (OSError, ValueError, KeyError, StopIteration, ZeroDivisionError) as error:
            result = {'text': '?', 'tooltip': f'{args.metric.upper()}: unavailable ({error})', 'class': ['usage-wheel', 'unavailable']}
        print(json.dumps(result), flush=True)
        if args.once:
            return
        time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass
