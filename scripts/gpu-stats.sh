#!/bin/bash

# Try card0, fall back to card1 if needed
CARD="card0"
SYS_PATH="/sys/class/drm/$CARD/device"

if [ ! -d "$SYS_PATH" ]; then
  CARD="card1"
  SYS_PATH="/sys/class/drm/$CARD/device"
fi

GPU_USAGE_FILE="$SYS_PATH/gpu_busy_percent"
VRAM_USED_FILE="$SYS_PATH/mem_info_vram_used"

# ---------- GPU usage ----------
GPU_USAGE=0
if [ -r "$GPU_USAGE_FILE" ]; then
  GPU_USAGE=$(cat "$GPU_USAGE_FILE")
fi

# ---------- VRAM used (GB) ----------
USED_GB=""
if [ -r "$VRAM_USED_FILE" ]; then
  RAW_USED=$(cat "$VRAM_USED_FILE")
  if [ "$RAW_USED" -gt 0 ] 2>/dev/null; then
    USED_GB=$(awk "BEGIN {printf \"%.2f\", $RAW_USED/1024/1024/1024}")
  fi
fi

# ---------- GPU temperature (°C) ----------
GPU_TEMP=""
# Find first hwmon under this card
HWMON_DIR=$(ls -d "$SYS_PATH"/hwmon/hwmon* 2>/dev/null | head -n 1)

if [ -n "$HWMON_DIR" ] && [ -r "$HWMON_DIR/temp1_input" ]; then
  RAW_TEMP=$(cat "$HWMON_DIR/temp1_input")
  # temp1_input is usually in millidegrees C
  GPU_TEMP=$((RAW_TEMP / 1000))
fi

# ---------- Output formatting ----------
# Icons:
# 󰢮  GPU usage, 󰘚 VRAM, 󰈸 temp (or change to whatever you like)

OUTPUT="󰢮  ${GPU_USAGE}%"

if [ -n "$USED_GB" ]; then
  OUTPUT="$OUTPUT  󰘚  ${USED_GB}GB"
fi

if [ -n "$GPU_TEMP" ]; then
  OUTPUT="$OUTPUT  󰈸  ${GPU_TEMP}°C"
fi

echo "$OUTPUT"
