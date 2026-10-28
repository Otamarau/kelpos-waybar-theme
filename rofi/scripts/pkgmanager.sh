#!/bin/bash

# Search for packages using yay
query=$(rofi -dmenu -p "Search package" -no-fixed-num-lines)

[[ -z "$query" ]] && exit 0

# Get matching packages (repo + AUR)
results=$(yay -Ss "$query" | sed -E 's/^[^/]+\/([^ ]+).*/\1/' | sort -u)

[[ -z "$results" ]] && echo "No results" | rofi -dmenu && exit 0

# Choose package
pkg=$(echo "$results" | rofi -dmenu -p "Select package")

[[ -z "$pkg" ]] && exit 0

# Show actions
action=$(printf "Install\nRemove\nInfo" | rofi -dmenu -p "$pkg")

case "$action" in
  Install)
    kitty -e bash -c "yay -S $pkg"
    ;;
  Remove)
    kitty -e bash -c "yay -Rns $pkg"
    ;;
  Info)
    yay -Si "$pkg" | rofi -dmenu -p "Info" -no-fixed-num-lines
    ;;
esac
