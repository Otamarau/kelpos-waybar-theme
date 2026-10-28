#!/bin/bash

########################
# 1. GEOLOCATION (IP)  #
########################

# Try to detect location from IP
GEO_JSON=$(curl -fsS --connect-timeout 2 --max-time 4 "https://ipapi.co/json/" 2>/dev/null)

# Default to Brisbane if anything fails
LAT="-27.47"
LON="153.03"
LOCATION="Brisbane, AU"

if [[ -n "$GEO_JSON" ]]; then
  if command -v jq >/dev/null 2>&1; then
    glat=$(echo "$GEO_JSON" | jq '.latitude' 2>/dev/null)
    glon=$(echo "$GEO_JSON" | jq '.longitude' 2>/dev/null)
    gcity=$(echo "$GEO_JSON" | jq -r '.city // empty' 2>/dev/null)
    gregion=$(echo "$GEO_JSON" | jq -r '.region // empty' 2>/dev/null)
    gcountry=$(echo "$GEO_JSON" | jq -r '.country_name // .country // empty' 2>/dev/null)
  else
    # crude fallback JSON parsing without jq
    glat=$(echo "$GEO_JSON" | sed -n 's/.*"latitude":\([^,}]*\).*/\1/p' | head -n1)
    glon=$(echo "$GEO_JSON" | sed -n 's/.*"longitude":\([^,}]*\).*/\1/p' | head -n1)
    gcity=$(echo "$GEO_JSON" | sed -n 's/.*"city":"\([^"]*\)".*/\1/p' | head -n1)
    gregion=$(echo "$GEO_JSON" | sed -n 's/.*"region":"\([^"]*\)".*/\1/p' | head -n1)
    gcountry=$(echo "$GEO_JSON" | sed -n 's/.*"country_name":"\([^"]*\)".*/\1/p' | head -n1)
    if [[ -z "$gcountry" ]]; then
      gcountry=$(echo "$GEO_JSON" | sed -n 's/.*"country":"\([^"]*\)".*/\1/p' | head -n1)
    fi
  fi

  # If we successfully got numbers, override defaults
  if [[ -n "$glat" && -n "$glon" ]]; then
    LAT="$glat"
    LON="$glon"
  fi

  # Build a human-readable location string if available
  if [[ -n "$gcity" || -n "$gregion" || -n "$gcountry" ]]; then
    parts=()
    [[ -n "$gcity" ]] && parts+=("$gcity")
    [[ -n "$gregion" ]] && parts+=("$gregion")
    [[ -n "$gcountry" ]] && parts+=("$gcountry")
    IFS=", " LOCATION="${parts[*]}"
    unset IFS
  fi
fi

##############################
# 2. WEATHER API FALLBACKS   #
##############################

TEMP_RAW=""
CONDITION=""
SOURCE=""

normalize_condition() {
  local c
  c=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')

  case "$c" in
    *thunder*|*storm*) echo "Storm" ;;
    *snow*|*sleet*|*hail*) echo "Snow" ;;
    *freezing*rain*) echo "Freezing Rain" ;;
    *drizzle*) echo "Drizzle" ;;
    *rain*|*shower*) echo "Rain" ;;
    *fog*|*mist*|*haze*) echo "Fog" ;;
    *cloud*)
      if [[ "$c" == *partly* || "$c" == *fair* ]]; then
        echo "Partly"
      else
        echo "Cloudy"
      fi
      ;;
    *clear*|*sunny*) echo "Clear" ;;
    *) echo "Unknown" ;;
  esac
}

try_open_meteo() {
  local json temp code
  json=$(curl -fsS --connect-timeout 3 --max-time 6 \
    "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,weather_code" 2>/dev/null) || return 1

  if command -v jq >/dev/null 2>&1; then
    temp=$(echo "$json" | jq -r '.current.temperature_2m // empty' 2>/dev/null)
    code=$(echo "$json" | jq -r '.current.weather_code // empty' 2>/dev/null)
  else
    temp=$(echo "$json" | sed -n 's/.*"temperature_2m":\([^,}]*\).*/\1/p' | head -n1)
    code=$(echo "$json" | sed -n 's/.*"weather_code":\([^,}]*\).*/\1/p' | head -n1)
  fi

  [[ -z "$temp" || -z "$code" ]] && return 1

  case "$code" in
    0) CONDITION="Clear" ;;
    1|2) CONDITION="Partly" ;;
    3) CONDITION="Cloudy" ;;
    45|48) CONDITION="Fog" ;;
    51|53|55) CONDITION="Drizzle" ;;
    61|63|65|80|81|82) CONDITION="Rain" ;;
    66|67) CONDITION="Freezing Rain" ;;
    71|73|75|77) CONDITION="Snow" ;;
    95|96|99) CONDITION="Storm" ;;
    *) CONDITION="Unknown" ;;
  esac

  TEMP_RAW="$temp"
  SOURCE="open-meteo"
  return 0
}

try_wttr() {
  local json temp desc code
  json=$(curl -fsS --connect-timeout 3 --max-time 6 \
    "https://wttr.in/${LAT},${LON}?format=j1" 2>/dev/null) || return 1

  if command -v jq >/dev/null 2>&1; then
    temp=$(echo "$json" | jq -r '.current_condition[0].temp_C // empty' 2>/dev/null)
    desc=$(echo "$json" | jq -r '.current_condition[0].weatherDesc[0].value // empty' 2>/dev/null)
    code=$(echo "$json" | jq -r '.current_condition[0].weatherCode // empty' 2>/dev/null)
  else
    temp=$(echo "$json" | sed -n 's/.*"temp_C":"\([^"]*\)".*/\1/p' | head -n1)
    desc=$(echo "$json" | sed -n 's/.*"weatherDesc":\[{"value":"\([^"]*\)"}.*/\1/p' | head -n1)
    code=$(echo "$json" | sed -n 's/.*"weatherCode":"\([^"]*\)".*/\1/p' | head -n1)
  fi

  [[ -z "$temp" ]] && return 1

  if [[ -n "$desc" ]]; then
    CONDITION=$(normalize_condition "$desc")
  else
    case "$code" in
      113) CONDITION="Clear" ;;
      116) CONDITION="Partly" ;;
      119|122) CONDITION="Cloudy" ;;
      143|248|260) CONDITION="Fog" ;;
      176|293|296|299|302|305|308|353|356|359) CONDITION="Rain" ;;
      179|182|185|227|230|281|284|311|314|317|320|323|326|329|332|335|338|350|362|365|368|371|374|377|386|389|392|395) CONDITION="Snow" ;;
      200) CONDITION="Storm" ;;
      *) CONDITION="Unknown" ;;
    esac
  fi

  TEMP_RAW="$temp"
  SOURCE="wttr.in"
  return 0
}

try_metno() {
  local json temp symbol
  json=$(curl -fsS --connect-timeout 3 --max-time 6 \
    -H "User-Agent: waybar-weather-script/1.0" \
    "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=${LAT}&lon=${LON}" 2>/dev/null) || return 1

  if command -v jq >/dev/null 2>&1; then
    temp=$(echo "$json" | jq -r '.properties.timeseries[0].data.instant.details.air_temperature // empty' 2>/dev/null)
    symbol=$(echo "$json" | jq -r '.properties.timeseries[0].data.next_1_hours.summary.symbol_code // .properties.timeseries[0].data.next_6_hours.summary.symbol_code // .properties.timeseries[0].data.next_12_hours.summary.symbol_code // empty' 2>/dev/null)
  else
    temp=$(echo "$json" | sed -n 's/.*"air_temperature":\([^,}]*\).*/\1/p' | head -n1)
    symbol=$(echo "$json" | sed -n 's/.*"symbol_code":"\([^"]*\)".*/\1/p' | head -n1)
  fi

  [[ -z "$temp" ]] && return 1

  CONDITION=$(normalize_condition "$symbol")
  TEMP_RAW="$temp"
  SOURCE="met.no"
  return 0
}

if ! try_open_meteo && ! try_wttr && ! try_metno; then
  echo " N/A"
  exit 0
fi

TEMP=$(echo "$TEMP_RAW" | sed 's/\.0$//')
TEMP="${TEMP}°C"

########################
# 3. ICON MAPPING      #
########################

HOUR=$(date +"%H")
ICON="" # fallback icon

# ---- ICON SET ----
DAY_CLEAR="󰖙"
DAY_PARTLY="󰖕"
DAY_CLOUDY="󰖐"
DAY_RAIN="󰖖"
DAY_DRIZZLE="󰖗"
DAY_STORM="󰙾"
DAY_FOG="󰼲"

NIGHT_CLEAR=""
NIGHT_PARTLY="󰼱"
NIGHT_RAIN="󰖖"
NIGHT_STORM="󰙾"
NIGHT_FOG="󰖑"

# Night hours: 6pm → 6am
is_night=false
(( HOUR >= 18 || HOUR < 6 )) && is_night=true

if $is_night; then
  case "$CONDITION" in
    Clear) ICON="$NIGHT_CLEAR" ;;
    Partly|Cloudy) ICON="$NIGHT_PARTLY" ;;
    Rain|Drizzle|Freezing\ Rain|Snow) ICON="$NIGHT_RAIN" ;;
    Storm) ICON="$NIGHT_STORM" ;;
    Fog) ICON="$NIGHT_FOG" ;;
    *) ICON="" ;;
  esac
else
  case "$CONDITION" in
    Clear) ICON="$DAY_CLEAR" ;;
    Partly) ICON="$DAY_PARTLY" ;;
    Cloudy) ICON="$DAY_CLOUDY" ;;
    Rain|Freezing\ Rain|Snow) ICON="$DAY_RAIN" ;;
    Drizzle) ICON="$DAY_DRIZZLE" ;;
    Storm) ICON="$DAY_STORM" ;;
    Fog) ICON="$DAY_FOG" ;;
    *) ICON="" ;;
  esac
fi

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

TEXT="$ICON  $TEMP"
TOOLTIP="Location: $LOCATION
$CONDITION, $TEMP
Source: $SOURCE"

printf '{"text":"%s","tooltip":"%s"}\n' "$(json_escape "$TEXT")" "$(json_escape "$TOOLTIP")"
