#!/usr/bin/env bash
# Waybar CPU temperature script
# - Bar: one main temp (integer °C)
# - Tooltip: cleaned per-core + die/ccd temps (no decimals, no high/crit)

set -euo pipefail

SENSORS_OUT="$(sensors 2>/dev/null || true)"

if [[ -z "$SENSORS_OUT" ]]; then
  printf '{"text":"  ?°C","tooltip":"No sensor data"}\n'
  exit 0
fi

# Grab only relevant lines (tweak the regex if your labels differ)
# Then:
#  - drop anything after "(" to remove high/crit/etc
#  - remove leading "+"
#  - turn ".0°C" into "°C"
#  - trim trailing spaces
relevant="$(
  echo "$SENSORS_OUT" \
    | grep -E '^(Core [0-9]+:|Tdie:|Tctl:|Tccd[0-9]+:|Package id 0:)' \
    | sed -E 's/[[:space:]]*\(.*$//; s/\+//g; s/\.0°C/°C/g; s/[[:space:]]+$//'
)"

# If nothing matched, fall back to first temperature-looking line
if [[ -z "$relevant" ]]; then
  relevant="$(
    echo "$SENSORS_OUT" \
      | grep -m1 -E ':[[:space:]]*\+?[0-9]+(\.[0-9]+)?°C' \
      | sed -E 's/[[:space:]]*\(.*$//; s/\+//g; s/\.0°C/°C/g; s/[[:space:]]+$//'
  )"
fi

# Renumber Core lines sequentially (optional, but fixes "Core 33" looking weird)
# Comment this block out if you want the original core numbering preserved.
relevant="$(
  echo "$relevant" | awk '
    BEGIN{c=0}
    /^Core [0-9]+:/{
      sub(/^Core [0-9]+:/, "Core " c ":")
      c++
    }
    {print}
  '
)"

# Pick main temp:
# prefer Tdie -> Tctl -> Package -> first Core
main="$(
  echo "$relevant" | awk '
    function intval(x){ gsub(/°C/,"",x); return int(x) }
    /^Tdie:/          {print intval($2); exit}
    /^Tctl:/          {print intval($2); exit}
    /^Package id 0:/  {print intval($4); exit}
    /^Core [0-9]+:/   {print intval($3); exit}
  '
)"

if [[ -z "${main:-}" ]]; then
  main="?"
fi

# Escape for JSON tooltip
tooltip="$(echo "$relevant" | sed ':a;N;$!ba;s/\n/\\n/g; s/"/\\"/g')"

printf '{"text":"  %s°C","tooltip":"%s"}\n' "$main" "$tooltip"
