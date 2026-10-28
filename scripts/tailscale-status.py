#!/usr/bin/env python3
"""Report Tailscale connection and exit-node status for Waybar."""

import html
import json
import subprocess


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


def main():
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, check=True, timeout=3,
        )
        output = indicator(json.loads(result.stdout))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError):
        output = {"text": "\u00a0", "class": "warning", "tooltip": "Tailscale: status unavailable"}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
