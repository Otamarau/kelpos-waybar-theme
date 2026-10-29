#!/usr/bin/env bash
# Waybar CPU temperature script
# - Shows one main temp in the bar (integer °C)
# - Tooltip shows per-core / die temps (no decimals)

# Get relevant temperature lines
core_lines="$(sensors \
  | grep -E 'Core [0-9]+:|Tdie:|Tctl:|Tccd[0-9]:' \
  | sed -E 's/ *\([^)]*\)//g; s/\+//g; s/\.0°C/°C/g')"

# Pick main temp: prefer Tdie/Tctl, else Core 0
main="$(echo "$core_lines" | grep -E 'Tdie:|Tctl:' | head -n1 | awk '{print int($2)}')"
if [[ -z "$main" ]]; then
  main="$(echo "$core_lines" | grep -E 'Core 0:' | head -n1 | awk '{print int($3)}')"
fi

# Fallback if sensors not ready
if [[ -z "$main" ]]; then
  main="?"
  core_lines="No sensor data (run sensors-detect)"
fi

# Escape newlines for JSON tooltip
tooltip="$(echo "$core_lines" | sed ':a;N;$!ba;s/\n/\\n/g')"

# Output JSON for Waybar
printf '{"text":" %3s°C","tooltip":"%s"}\n' "$main" "$tooltip"
