#!/usr/bin/env bash

close_rofi() {
  pkill -x rofi 2>/dev/null || true
  pkill -x rofi-wayland 2>/dev/null || true
}

# If rofi is already running, kill it (close menu)
if pgrep -x rofi >/dev/null || pgrep -x rofi-wayland >/dev/null; then
  close_rofi
  exit 0
fi

# Otherwise, launch your usual rofi command
rofi -show drun -click-to-exit

# Some launchers keep the menu process around after handing off an app.
# Ensure it is gone once the selected application has been opened.
close_rofi
# or if you normally use something else, e.g.:
# rofi -show drun -modi drun,run,calc,clipboard
