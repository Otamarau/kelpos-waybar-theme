#!/usr/bin/env python3
"""Report Tailscale connection and exit-node status for Waybar."""

import html
import json
import subprocess
import sys
import time
from pathlib import Path


def indicator(status):
    state = status.get("BackendState", "Unknown")
    css = "disconnected"
    lines = [f"Tailscale: {state}"]
    if state == "Running":
        css = "connected"
        lines = ["Tailscale: connected"]
        addresses = status.get("TailscaleIPs") or []
        if addresses:
            lines.append(f"IP: {addresses[0]}")
        exit_node = status.get("ExitNodeStatus")
        if exit_node:
            peers = (status.get("Peer") or {}).values()
            peer = next((p for p in peers if p.get("ID") == exit_node.get("ID")), {})
            name = peer.get("HostName") or next(iter(exit_node.get("TailscaleIPs") or []), "Unknown")
            online = exit_node.get("Online", False)
            css = "exit-node" if online else "warning"
            lines.append(f"Exit node: {name} ({'online' if online else 'offline'})")
        else:
            lines.append("Exit node: none (tailnet only)")
        if not (status.get("Self") or {}).get("Online", False):
            css = "warning"
            lines.append("Connection to Tailscale control server is offline")
    elif state == "Stopped":
        lines = ["Tailscale: off"]
    else:
        css = "warning"
    lines.extend(status.get("Health") or [])
    return {"text": "\u00a0", "class": css, "tooltip": html.escape("\n".join(lines))}


def tailscale_status():
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, check=True, timeout=3,
        )
        output = indicator(json.loads(result.stdout))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError):
        output = {"text": "\u00a0", "class": "warning", "tooltip": "Tailscale: status unavailable"}
    return output


def network_counters():
    """Count physical uplinks once, excluding VPN/bridge copies of their traffic."""
    counters = {}
    for device in Path('/sys/class/net').iterdir():
        try:
            if not (device / 'device').exists():
                continue
            if (device / 'operstate').read_text().strip() not in ('up', 'unknown'):
                continue
            counters[device.name] = tuple(
                int((device / 'statistics' / field).read_text())
                for field in ('rx_bytes', 'tx_bytes')
            )
        except (OSError, ValueError):
            continue
    return counters


def transfer_rates(current, previous, elapsed):
    if elapsed <= 0:
        return 0.0, 0.0
    return tuple(sum(max(0, values[i] - previous[name][i])
                     for name, values in current.items() if name in previous) / elapsed
                 for i in (0, 1))


def format_rate(value):
    for unit in ('B/s', 'KiB/s', 'MiB/s', 'GiB/s'):
        if value < 1024 or unit == 'GiB/s':
            return f'{value:.1f} {unit}'
        value /= 1024


def main():
    if '--stream' not in sys.argv:
        print(json.dumps(tailscale_status(), ensure_ascii=False))
        return
    previous = network_counters()
    sampled = time.monotonic()
    status = None
    refresh_at = 0
    while True:
        if time.monotonic() >= refresh_at:
            status = tailscale_status()
            refresh_at = time.monotonic() + 5
        time.sleep(max(0, 1 - (time.monotonic() - sampled)))
        current = network_counters()
        now = time.monotonic()
        down, up = transfer_rates(current, previous, now - sampled)
        previous, sampled = current, now
        output = dict(status)
        if current:
            network = ('Network usage · ' + ', '.join(sorted(current))
                       + f'\n↓ Download: {format_rate(down)}'
                       + f'\n↑ Upload: {format_rate(up)}'
                       + '\nTotal interface traffic (including Tailscale)')
        else:
            network = 'Network usage: no active physical interface'
        output['tooltip'] += '\n\n' + html.escape(network)
        print(json.dumps(output, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
