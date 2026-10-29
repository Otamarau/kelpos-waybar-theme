#!/usr/bin/env bash

# If rofi is already running, kill it (close menu)
if pgrep -x rofi >/dev/null || pgrep -x rofi-wayland >/dev/null; then
  pkill rofi
  pkill rofi-wayland
  exit 0
fi

# Otherwise, launch your usual rofi command
rofi -show drun -click-to-exit
# or if you normally use something else, e.g.:
# rofi -show drun -modi drun,run,calc,clipboard
