#!/bin/bash

meminfo=$(</proc/meminfo)
swap_total_kb=$(printf '%s\n' "$meminfo" | awk '/^SwapTotal:/ {print $2}')
swap_free_kb=$(printf '%s\n' "$meminfo" | awk '/^SwapFree:/ {print $2}')

if [[ -z "$swap_total_kb" || "$swap_total_kb" -le 0 ]]; then
  printf '{"text":"󰁪  N/A","tooltip":"Swap: disabled"}\n'
  exit 0
fi

swap_used_kb=$((swap_total_kb - swap_free_kb))
swap_used_pct=$((swap_used_kb * 100 / swap_total_kb))

swap_used_gb=$(awk "BEGIN {printf \"%.1f\", $swap_used_kb/1024/1024}")
swap_total_gb=$(awk "BEGIN {printf \"%.1f\", $swap_total_kb/1024/1024}")

printf '{"text":"󰁪  %s%%","tooltip":"Swap: %sGB / %sGB (%s%%)"}\n' \
  "$swap_used_pct" "$swap_used_gb" "$swap_total_gb" "$swap_used_pct"
