#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIFI_MODE="$SCRIPT_DIR/quick-controls-wifi.sh"
BLUETOOTH_MODE="$SCRIPT_DIR/quick-controls-bluetooth.sh"
POWER_MODE="$SCRIPT_DIR/quick-controls-power.sh"

for mode_script in "$WIFI_MODE" "$BLUETOOTH_MODE" "$POWER_MODE"; do
  if [ ! -x "$mode_script" ]; then
    notify-send "Waybar" "Quick controls mode script missing or not executable: $mode_script"
    exit 1
  fi
done

rofi \
  -show "󰤨" \
  -p "Quick" \
  -theme-str 'prompt { font: "JetBrainsMono Nerd Font Propo 12"; padding: 0px 6px 0px 2px; }' \
  -sidebar-mode true \
  -modi "󰤨:$WIFI_MODE,󰂯:$BLUETOOTH_MODE,󰐥:$POWER_MODE"
