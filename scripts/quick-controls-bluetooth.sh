#!/usr/bin/env bash
set -euo pipefail

# Bound commands so an unavailable Bluetooth service cannot hang the menu.
bt() {
  local limit=20s
  case "${1:-}" in show|devices|info) limit=3s ;; esac
  # bluetoothctl --timeout delays even completed queries; use only an outer limit.
  LC_ALL=C timeout "$limit" bluetoothctl "$@" 2>/dev/null
}

status=""
refresh_id=""
refreshing=false
refresh_result="Bluetooth devices refreshed."

refresh_notification() {
  local message="$1" duration="$2"
  local -a options=(--print-id --transient --app-name 'Quick Menu' --expire-time "$duration")
  [[ "$refresh_id" =~ ^[0-9]+$ ]] && options+=(--replace-id "$refresh_id")
  timeout 2s notify-send "${options[@]}" Bluetooth "$message" 2>/dev/null || true
}

print_menu() {
  local controller powered devices kind mac name info
  printf '\0no-custom\x1ftrue\n\0keep-selection\x1ftrue\n\0keep-filter\x1ftrue\n'
  controller="$(bt show || true)"
  powered="$(awk '/^[[:space:]]*Powered:/{print $2; exit}' <<< "$controller")"
  if [ -z "$powered" ]; then
    refresh_result="Could not refresh: Bluetooth is unavailable."
    printf '\0message\x1fBluetooth unavailable. Check the adapter or Bluetooth service.\n'
    printf 'Open Bluetooth Manager\nRefresh\n'
    return
  fi

  if [ -n "$status" ]; then
    printf '\0message\x1f%s\n' "$status"
  else
    printf '\0message\x1fSelect a device to connect or disconnect.\n'
  fi

  if [ "$powered" = "yes" ]; then
    printf 'Disable Bluetooth\n'
  else
    printf 'Enable Bluetooth\n'
  fi
  printf 'Open Bluetooth Manager\nRefresh\n'
  [ "$powered" = "yes" ] || return 0

  if ! devices="$(bt devices)"; then
    refresh_result="Could not refresh Bluetooth devices."
    printf '\0message\x1fCould not read Bluetooth devices. Try Refresh.\n'
    return
  fi
  while read -r kind mac name; do
    [ "$kind" = "Device" ] || continue
    [[ "$mac" =~ ^([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}$ ]] || continue
    name="${name:-Unknown device}"
    if ! info="$(bt info "$mac")"; then
      refresh_result="Refreshed with some device details unavailable."
    fi
    if connected "$info"; then
      printf '● %s [%s]\n' "$name" "$mac"
    else
      printf '○ %s [%s]\n' "$name" "$mac"
    fi
  done <<< "$devices"
}

connected() {
  [[ "$1" =~ (^|$'\n')[[:blank:]]*Connected:[[:blank:]]+yes([[:space:]]|$) ]]
}

toggle_connection() {
  local mac info
  [[ "$1" =~ \[(([[:xdigit:]]{2}:){5}[[:xdigit:]]{2})\]$ ]] || return 0
  mac="${BASH_REMATCH[1]}"
  if ! info="$(bt info "$mac")"; then
    status="Could not read device status. Try Refresh."
    return
  fi
  if connected "$info"; then
    if bt disconnect "$mac" >/dev/null; then
      status="Device disconnected."
    else
      status="Could not disconnect the device. Try again."
    fi
  elif bt connect "$mac" >/dev/null; then
    status="Device connected."
  else
    # Pairing may require a PIN or confirmation that this menu cannot provide.
    status="Could not connect. Check the device is available and paired."
  fi
}

if [ "${ROFI_RETV:-0}" = 1 ]; then
  case "${1:-}" in
    "Enable Bluetooth")
      if bt power on >/dev/null; then
        status="Bluetooth enabled."
      else
        status="Could not enable Bluetooth. Check the adapter or radio block."
      fi
      ;;
    "Disable Bluetooth")
      if bt power off >/dev/null; then
        status="Bluetooth disabled."
      else
        status="Could not disable Bluetooth."
      fi
      ;;
    "Open Bluetooth Manager")
      if command -v overskride >/dev/null 2>&1; then
        nohup overskride </dev/null >/dev/null 2>&1 &
        exit 0
      fi
      if command -v blueman-manager >/dev/null 2>&1; then
        nohup blueman-manager </dev/null >/dev/null 2>&1 &
        exit 0
      fi
      status="Install Overskride or Blueman for pairing and advanced controls."
      ;;
    "Refresh")
      refreshing=true
      refresh_id="$(refresh_notification 'Refreshing Bluetooth devices…' 15000)"
      ;;
    *) toggle_connection "${1:-}" ;;
  esac
fi

# Rofi closes script modes when an action returns no rows.
print_menu
if "$refreshing"; then
  refresh_notification "$refresh_result" 2000 >/dev/null
fi

