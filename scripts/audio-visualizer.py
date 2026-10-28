#!/usr/bin/env python3
"""Stream Cava's output as five audio bars for a Waybar custom module."""

import json
from pathlib import Path
import signal
import subprocess
import sys


LEVELS = "▁▂▃▄▅▆▇█"


def stop(_signum, _frame):
    raise SystemExit(0)


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    config = Path(__file__).with_name("cava-waybar.conf")
    reverse = "--reverse" in sys.argv
    process = subprocess.Popen(
        ["cava", "-p", str(config)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    )
    previous = None
    try:
        for line in process.stdout:
            try:
                values = [int(value) for value in line.strip().split(";") if value]
            except ValueError:
                continue
            if len(values) != 5:
                continue
            if reverse:
                values.reverse()
            output = json.dumps({
                "text": "".join(LEVELS[max(0, min(7, value))] for value in values),
                "class": "playing" if any(values) else "silent",
            })
            if output != previous:
                print(output, flush=True)
                previous = output
    except BrokenPipeError:
        pass
    finally:
        # Waybar reloads must also stop the Cava child process.
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
