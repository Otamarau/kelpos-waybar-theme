#!/usr/bin/env bash
set -euo pipefail

if [ "${ROFI_RETV:-0}" -eq 0 ]; then
  printf '⏻  Power Off\n'
  printf '󰜉  Reboot\n'
  printf '󰍃  Logout\n'
  printf '󰌾  Lock\n'
  exit 0
fi

case "${1:-}" in
  "⏻  Power Off")
    systemctl poweroff
    ;;
  "󰜉  Reboot")
    systemctl reboot
    ;;
  "󰍃  Logout")
    hyprctl dispatch 'hl.dsp.exit()'
    ;;
  "󰌾  Lock")
    python3 "$HOME/.config/hypr/lock-with-cava.py"
    ;;
esac
