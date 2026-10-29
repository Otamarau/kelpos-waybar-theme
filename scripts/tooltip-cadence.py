#!/usr/bin/env python3
"""Batch custom-module updates on shared one-second boundaries for GTK tooltips.

Waybar rewrites tooltip markup for every output line. Independently timed
modules can repeatedly reset GTK's global 500ms tooltip delay. Polling and
streaming commands collect in the background; only changed output is published.
"""

import argparse
import json
import queue
import subprocess
import threading
import time


def collect(command, interval, updates):
    if interval is None:
        with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
            for line in process.stdout:
                updates.put(line.rstrip('\n'))
        updates.put(None)
        return
    while True:
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stdout.strip():
            updates.put(result.stdout.strip().splitlines()[-1])
        else:
            updates.put(json.dumps({'text': '', 'tooltip': '', 'class': 'unavailable'}))
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval', type=float)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or (args.interval is not None and args.interval <= 0):
        parser.error('provide a command and a positive polling interval')
    updates = queue.Queue()
    threading.Thread(target=collect, args=(command, args.interval, updates), daemon=True).start()
    previous = None
    while True:
        # Wall-clock boundaries are shared by all wrapper instances/monitors.
        time.sleep(max(0.001, 1 - time.time() % 1))
        latest = None
        finished = False
        while True:
            try:
                line = updates.get_nowait()
            except queue.Empty:
                break
            if line is None:
                finished = True
            else:
                latest = line
        if latest is not None and latest != previous:
            print(latest, flush=True)
            previous = latest
        if finished:
            return


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:
        pass

