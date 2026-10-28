#!/usr/bin/env bash
set -euo pipefail

DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
FILE="$DIR/$(date +'%Y-%m-%d_%H-%M-%S').png"

# area select -> save -> copy to clipboard
slurp | grim -g - "$FILE"
wl-copy < "$FILE"

notify-send "Screenshot saved" "$FILE (copied to clipboard)"
