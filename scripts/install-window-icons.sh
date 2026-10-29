#!/usr/bin/env bash
# From Otamarau/kelpos-waybar-theme: Rofi window mode uses lowercase app IDs.
set -euo pipefail
icon_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
mkdir -p "$icon_dir"
link_icon() {
  local name="$1" source="$2"
  [ -f "$source" ] || return 0
  # Preserve any user-supplied icon with this name.
  if [ ! -e "$icon_dir/$name.png" ] && [ ! -L "$icon_dir/$name.png" ]; then
    ln -s "$source" "$icon_dir/$name.png"
  fi
}
link_icon com.microsoft.vscode /usr/share/pixmaps/vscode.png
link_icon monero-core /usr/share/icons/hicolor/256x256/apps/org.getmonero.Monero.png
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t "${icon_dir%/256x256/apps}"
fi
