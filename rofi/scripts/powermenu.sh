#!/bin/bash

options=$'⏻  Power Off\n  Reboot\n  Logout\n󰍃   Lock'

chosen="$(echo -e "$options" \
    | rofi -dmenu -i -p "󰍹 " -lines 4 -no-show-icons)"

case "$chosen" in
  *"Power Off"*) systemctl poweroff ;;
  *"Reboot"*)    systemctl reboot ;;
  *"Logout"*)    hyprctl dispatch 'hl.dsp.exit()' ;;
  *"Lock"*)      hyprlock ;;
esac
