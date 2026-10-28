#!/bin/sh
# Waybar automatically reloads its stylesheet when this colour changes.
case "$1" in
  opaque) colour='#000000' ;;
  transparent) colour='rgba(0, 0, 0, 0.85)' ;;
  *) exit 1 ;;
esac

sed -i "s/^@define-color waybar_background .*;/@define-color waybar_background $colour;/" \
  "$HOME/.config/waybar/style.css"
