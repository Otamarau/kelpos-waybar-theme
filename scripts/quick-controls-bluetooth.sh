#!/usr/bin/env bash
set -euo pipefail

notify() {
  command -v notify-send >/dev/null 2>&1 && notify-send "Waybar" "$1"
}

bt_powered() {
  bluetoothctl show 2>/dev/null | awk '/Powered:/{print $2; exit}'
}

print_menu() {
  local powered
  powered="$(bt_powered || true)"

  if [ "$powered" = "yes" ]; then
    printf 'Disable Bluetooth\n'
  else
    printf 'Enable Bluetooth\n'
  fi

  printf 'Open Overskride\n'
  printf 'Refresh\n'

  [ "$powered" = "yes" ] || exit 0

  bluetoothctl devices 2>/dev/null | while read -r _ mac name; do
    [ -n "${mac:-}" ] || continue
    [ -n "${name:-}" ] || name="Unknown device"

    if bluetoothctl info "$mac" 2>/dev/null | rg -q '^Connected: yes$'; then
      printf '● %s [%s]\n' "$name" "$mac"
    else
      printf '  %s [%s]\n' "$name" "$mac"
    fi
  done
}

toggle_connection() {
  local row mac
  row="$1"
  mac="$(printf '%s' "$row" | sed -nE 's/.*\[([^]]+)\]$/\1/p')"
  [ -n "$mac" ] || exit 0

  if bluetoothctl info "$mac" 2>/dev/null | rg -q '^Connected: yes$'; then
    bluetoothctl disconnect "$mac" >/dev/null 2>&1 && notify "Disconnected $mac"
    exit 0
  fi

  if bluetoothctl connect "$mac" >/dev/null 2>&1; then
    notify "Connected $mac"
    exit 0
  fi

  bluetoothctl pair "$mac" >/dev/null 2>&1 || true
  bluetoothctl trust "$mac" >/dev/null 2>&1 || true

  if bluetoothctl connect "$mac" >/dev/null 2>&1; then
    notify "Connected $mac"
  else
    notify "Failed to connect $mac"
  fi
}

if [ "${ROFI_RETV:-0}" -eq 0 ]; then
  print_menu
  exit 0
fi

case "${1:-}" in
  "Enable Bluetooth")
    bluetoothctl power on >/dev/null 2>&1 || notify "Could not enable Bluetooth"
    ;;
  "Disable Bluetooth")
    bluetoothctl power off >/dev/null 2>&1 || notify "Could not disable Bluetooth"
    ;;
  "Open Overskride")
    # Release Rofi's script output pipe without waiting for the application.
    nohup overskride </dev/null >/dev/null 2>&1 &
    exit 0
    ;;
  "Refresh")
    ;;
  *)
    toggle_connection "${1:-}"
    ;;
esac
