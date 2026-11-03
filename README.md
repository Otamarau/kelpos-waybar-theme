# Kelpos Waybar — laptop

This `laptop` branch contains the laptop configuration. The desktop version remains on `main`; keep updates to this setup on `laptop`.

## Features

- CPU, RAM and swap usage wheels, a font-based CPU icon and coloured CPU temperature.
- Consistent button spacing, border hover highlights and batched tooltip updates.
- Tailscale tooltip with live total physical-interface upload/download speeds. Right-click opens Wi-Fi controls.
- Battery, brightness, volume, weather, calendar, workspaces and screenshot/clipboard controls.
- Rofi Wi-Fi, Bluetooth, package search/install and power tabs. Advanced Bluetooth controls use Overskride or Blueman.
- Rofi window-icon aliases and optional compositor-side outside-click dismissal.

## Install

Clone this branch explicitly:

```sh
git clone --branch laptop https://github.com/Otamarau/kelpos-waybar-theme.git
cd kelpos-waybar-theme
backup="$HOME/.local/state/theme-backups/manual-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup" ~/.config/waybar ~/.config/rofi ~/.local/bin
cp -a ~/.config/waybar "$backup/waybar"
cp -a ~/.config/rofi "$backup/rofi"
cp config.jsonc style.css usage-wheels.css ~/.config/waybar/
cp -a scripts icons ~/.config/waybar/
cp -a rofi/. ~/.config/rofi/
install -m 755 bin/rofi-clipboard bin/rofi-toggle.sh bin/rofi-recent bin/rofi-record-launch ~/.local/bin/
bash ~/.config/waybar/scripts/install-window-icons.sh
pkill -USR2 -x waybar || true
```

Launch `waybar` if it is not already running. This branch uses `config.jsonc` directly, without the desktop responsive-layout launcher. Rofi changes apply when reopening a menu.

The app launcher uses the desktop branch's recent-app behaviour: an empty search shows recently launched apps first; typing fuzzy-matches app names and ranks results by match quality. Both the launcher shortcut and Waybar app button use `~/.local/bin/rofi-recent`. Launches through this wrapper are recorded in `$XDG_STATE_HOME/rofi/recent-apps.json` (default `~/.local/state/rofi/recent-apps.json`); existing Rofi history supplies the initial order. Launches outside the wrapper are not tracked. This requires Rofi 2.0 and Python GIO introspection, with `drun.DBusActivatable` disabled so launches pass through the recorder.

For Hyprland's Lua configuration, load `integrations/rofi-outside-click.lua` once using `dofile` with its installed absolute path, or copy its block into `hyprland.lua`, then run `hyprctl reload`. It closes mapped Rofi layers only for outside left-clicks and passes the click through. The Rofi `click-to-exit` flag alone does not supply this compositor behaviour on the source Wayland setup.

## Dependencies and laptop settings

Use Arch's system Python (`/usr/bin/python3`), PyGObject and libnm introspection. Install Waybar, Rofi, NetworkManager/nmcli, bluetoothctl, notify-send, JetBrainsMono Nerd Font (including Propo), Font Awesome and Adwaita icons. Package browsing uses pacman, yay and Kitty; installs remain interactive in the terminal.

Other actions use Mission Center, brightnessctl, pavucontrol/pactl, Tailscale, GNOME Calendar/Weather/Power Statistics, grim, slurp, wl-clipboard, cliphist and ImageMagick. Advanced networking uses nm-connection-editor and networkmanager_dmenu. Rofi's calculator needs its calc plugin. Review actions for applications you use.

Brightness is configured for `intel_backlight`. CPU sensors support coretemp, k10temp and zenpower. GPU wheels are not in the laptop layout. Weather falls back to Brisbane. Network rates count active physical interfaces and avoid double-counting the Tailscale tunnel.

The power menus expect the companion `kelpos-hyprlock-theme` **laptop** branch at `~/.config/hypr/`, including `lock-with-cava.py`. Logout uses this setup's Hyprland Lua dispatcher.

## Checks and updates

```sh
/usr/bin/python3 -m unittest discover -s tests/kelpos-port -v
```

The menu tests simulate devices and do not toggle real radios. Live desktop appearance, authentication and hardware actions need checking in your session. This snapshot excludes backups, caches, clipboard history and Rofi favourites. Icon attribution is in `icons/tailscale-source.txt`.

Copy future live edits into this checkout and push to `laptop`, not `main`.
