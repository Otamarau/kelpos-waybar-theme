#!/bin/bash

CACHE_FILE="/tmp/waybar-brisbane-weather-json.cache"
CACHE_TTL=1200 # 20 minutes

fetch_json() {
  local url="$1"
  curl -fsSL --connect-timeout 2 --max-time 4 "$url" 2>/dev/null
}

print_cached_or_na() {
  if [[ -s "$CACHE_FILE" ]]; then
    cached_output=$(cat "$CACHE_FILE")
    if [[ -n "$cached_output" && "$cached_output" != *null* ]]; then
      echo "$cached_output"
      return
    fi
  fi
  printf '%s\n' '{"text":"  N/A","tooltip":"Location: Brisbane, AU\nWeather unavailable"}'
}

# Reuse cached output to avoid API rate limits
if [[ -f "$CACHE_FILE" ]]; then
  now=$(date +%s)
  mtime=$(stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)
  age=$((now - mtime))

  if (( age < CACHE_TTL )); then
    cached_output=$(cat "$CACHE_FILE")
    if [[ -n "$cached_output" && "$cached_output" != *null* ]]; then
      echo "$cached_output"
      exit 0
    fi
  fi
fi

########################
# 1. LOCATION          #
########################

# Brisbane coordinates
LAT="-27.47"
LON="153.03"

##############################
# 2. CALL WEATHER APIs        #
##############################

API_SOURCE=""
TEMP=""
CODE=""

JSON=$(fetch_json \
  "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,weather_code")

if [[ -n "$JSON" ]]; then
  # Try to parse with jq if available
  if command -v jq >/dev/null 2>&1; then
    TEMP=$(echo "$JSON" | jq -r '.current.temperature_2m // empty' 2>/dev/null)
    CODE=$(echo "$JSON" | jq -r '.current.weather_code // empty' 2>/dev/null)
  else
    # whitespace-tolerant fallback parsing without jq
    TEMP=$(echo "$JSON" | tr -d '\n' | sed -n 's/.*"temperature_2m"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p' | head -n1)
    CODE=$(echo "$JSON" | tr -d '\n' | sed -n 's/.*"weather_code"[[:space:]]*:[[:space:]]*\([^,}]*\).*/\1/p' | head -n1)
  fi
fi

if [[ -n "$TEMP" && -n "$CODE" && "$TEMP" != "null" && "$CODE" != "null" ]]; then
  API_SOURCE="open-meteo"
else
  WTTR_JSON=$(fetch_json "https://wttr.in/${LAT},${LON}?format=j1")
  if [[ -n "$WTTR_JSON" ]]; then
    if command -v jq >/dev/null 2>&1; then
      TEMP=$(echo "$WTTR_JSON" | jq -r '.current_condition[0].temp_C // empty' 2>/dev/null)
      CODE=$(echo "$WTTR_JSON" | jq -r '.current_condition[0].weatherCode // empty' 2>/dev/null)
    else
      WTTR_ONELINE=$(echo "$WTTR_JSON" | tr -d '\n')
      TEMP=$(echo "$WTTR_ONELINE" | sed -n 's/.*"temp_C"[[:space:]]*:[[:space:]]*"\{0,1\}\([^",}]*\).*/\1/p' | head -n1)
      CODE=$(echo "$WTTR_ONELINE" | sed -n 's/.*"weatherCode"[[:space:]]*:[[:space:]]*"\{0,1\}\([^",}]*\).*/\1/p' | head -n1)
    fi

    if [[ -n "$TEMP" && -n "$CODE" && "$TEMP" != "null" && "$CODE" != "null" ]]; then
      API_SOURCE="wttr"
    fi
  fi
fi

if [[ -z "$API_SOURCE" ]]; then
  print_cached_or_na
  exit 0
fi

# Remove trailing .0 if present, then append °C once
TEMP=$(echo "$TEMP" | sed 's/\.0$//')
TEMP="${TEMP}°C"

########################
# 3. MAP TO CONDITION  #
########################

CONDITION="Unknown"
if [[ "$API_SOURCE" == "open-meteo" ]]; then
  case "$CODE" in
    0) CONDITION="Clear" ;;
    1|2) CONDITION="Partly" ;;            # mainly clear / partly cloudy
    3) CONDITION="Cloudy" ;;              # overcast
    45|48) CONDITION="Fog" ;;
    51|53|55) CONDITION="Drizzle" ;;
    61|63|65|80|81|82) CONDITION="Rain" ;; # various rain intensities / showers
    66|67) CONDITION="Freezing Rain" ;;
    71|73|75|77) CONDITION="Snow" ;;
    95|96|99) CONDITION="Storm" ;;        # thunderstorm
  esac
else
  case "$CODE" in
    113) CONDITION="Clear" ;;
    116) CONDITION="Partly" ;;
    119|122) CONDITION="Cloudy" ;;
    143|248|260) CONDITION="Fog" ;;
    176|263|266|293|296|299|302|305|308|353|356|359) CONDITION="Rain" ;;
    179|182|185|227|230|320|323|326|329|332|335|338|350|368|371|374|377) CONDITION="Snow" ;;
    200|386|389|392|395) CONDITION="Storm" ;;
  esac
fi

HOUR=$(date +"%H")

ICON="" # fallback icon

# ---- ICON SET ----
DAY_CLEAR="󰖙"
DAY_PARTLY="󰖕"
DAY_CLOUDY="󰖐"
DAY_OVERCAST="󰼵"
DAY_RAIN="󰖖"
DAY_HEAVY_RAIN="󰼳"
DAY_DRIZZLE="󰖗"
DAY_STORM="󰙾"
DAY_FOG="󰼲"
DAY_WIND="󰖝"

NIGHT_CLEAR=""
NIGHT_PARTLY="󰼱"
NIGHT_RAIN="󰖖"
NIGHT_STORM="󰙾"
NIGHT_FOG="󰖑"

# Night hours: 6pm → 6am
is_night=false
(( 10#$HOUR >= 18 || 10#$HOUR < 6 )) && is_night=true

########################
# 4. PICK ICON         #
########################

if $is_night; then
  case "$CONDITION" in
    Clear) ICON="$NIGHT_CLEAR" ;;
    Partly|Cloudy) ICON="$NIGHT_PARTLY" ;;
    Rain|Drizzle|Freezing\ Rain) ICON="$NIGHT_RAIN" ;;
    Storm) ICON="$NIGHT_STORM" ;;
    Fog) ICON="$NIGHT_FOG" ;;
    *) ICON="" ;;
  esac
else
  case "$CONDITION" in
    Clear) ICON="$DAY_CLEAR" ;;
    Partly) ICON="$DAY_PARTLY" ;;
    Cloudy) ICON="$DAY_CLOUDY" ;;
    Rain|Freezing\ Rain) ICON="$DAY_RAIN" ;;
    Drizzle) ICON="$DAY_DRIZZLE" ;;
    Storm) ICON="$DAY_STORM" ;;
    Fog) ICON="$DAY_FOG" ;;
    *) ICON="" ;;
  esac
fi

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

SOURCE="$API_SOURCE"
[[ "$SOURCE" == "wttr" ]] && SOURCE="wttr.in"
TOOLTIP="Location: Brisbane, AU
$CONDITION, $TEMP
Source: $SOURCE"
OUTPUT=$(printf '{"text":"%s","tooltip":"%s"}' "$(json_escape "$ICON  $TEMP")" "$(json_escape "$TOOLTIP")")
echo "$OUTPUT"
printf '%s\n' "$OUTPUT" > "$CACHE_FILE"
