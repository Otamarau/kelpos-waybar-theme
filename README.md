# Waybar

Personal Waybar and Rofi configuration for Arch Linux and Hyprland, with compact hardware gauges and a Rofi network menu.

## Features

- White CPU, RAM, swap, GPU and VRAM usage wheels with detailed tooltips.
- Per-thread CPU usage and compact per-core temperature tables.
- Colour-coded CPU/GPU temperatures.
- Fixed-width download/upload readings that dim when idle.
- Scrolling MPRIS media titles, album art, playback controls and Cava visualizers.
- Rofi Wi-Fi/Ethernet, Bluetooth and power controls.
- Weather, screenshots, Tailscale status, workspaces and a calendar clock.
- Rounded white hover borders that fade out without changing module spacing.
- Shared tooltip update timing to reduce GTK tooltip interruptions.

## Setup

This is a working desktop configuration, not a universal installer. Back up your existing Waybar directory, then place this repository at `~/.config/waybar`. Commands in the configuration assume that location.

Run:

```sh
python3 ~/.config/waybar/scripts/responsive-waybar.py
```

### Install the included Rofi setup

The `rofi/` directory is a snapshot of the accompanying Rofi configuration, themes and scripts. Back up any existing `~/.config/rofi` files before copying it into place. From this repository's root:

```sh
mkdir -p ~/.config/rofi ~/.local/bin
cp -a rofi/. ~/.config/rofi/
install -m 755 bin/rofi-clipboard bin/rofi-toggle.sh ~/.local/bin/
bash scripts/install-window-icons.sh
```

Rofi uses the installed Adwaita theme and application icons from hicolor. The icon setup script adds aliases for VS Code and Monero because the Wayland window switcher looks up lowercase window application IDs.

Launch with `rofi -show drun`, or use `~/.local/bin/rofi-toggle.sh` as a keyboard shortcut. The Quick Menu remains at `~/.config/waybar/scripts/quick-controls-rofi.sh`.

The copied Rofi files are separate from the repository: after editing your live `~/.config/rofi` setup, copy those changes back into `rofi/` before committing them. Clipboard history and generated image previews are not included.

The configuration was developed with Waybar 0.15.0, GTK 3, Rofi script mode and Python 3. Python uses PyGObject with the `NM`, `Playerctl`, `GdkPixbuf`, `GLib` and `Pango` introspection libraries. No pip virtual environment is required when these are supplied by the distribution.

### Dependencies by feature

| Feature | Programs / libraries |
| --- | --- |
| Bar and fonts | Waybar, GTK 3, JetBrainsMono Nerd Font (including Propo), Font Awesome |
| Network menu and readings | NetworkManager, nmcli, libnm introspection, iproute2, Rofi, notify-send |
| Advanced network setup | networkmanager_dmenu, nm-connection-editor |
| Media | Playerctl introspection, GdkPixbuf, an MPRIS player, Cava |
| Audio controls | PulseAudio-compatible server, pactl, pavucontrol |
| Hardware monitoring | Linux procfs/sysfs; lm-sensors for the legacy CPU-temperature script |
| Bluetooth | bluetoothctl, Overskride |
| Screenshots | grim, slurp, wl-copy, notify-send |
| Rofi clipboard previews | cliphist, wl-clipboard, ImageMagick (`magick`); clipboard history must be collected by your session |
| Rofi calculator / app icons | Rofi calc plugin, Adwaita icon theme |
| Standalone package menu | yay, kitty; launch `~/.config/rofi/scripts/pkgmanager.sh` separately |
| Weather | curl, jq (preferred), gnome-weather for the click action |
| Other click actions | missioncenter, gsimplecal, tailscale, hyprctl, hyprlock |

Install the dependencies for the features you use, or remove those modules from the layout.

### Machine-specific settings

- The responsive launcher reads Hyprland monitor sizes, rotation and scale. `config.jsonc` remains a static fallback for launching Waybar directly.
- GPU gauges currently require AMD-style `gpu_busy_percent` and VRAM counters in `/sys/class/drm`.
- CPU temperatures support `coretemp`, `k10temp` and `zenpower` sensors. Temperature colours use the sensors' reported limits, with fallback display thresholds when limits are absent.
- The weather script uses IP geolocation, falling back to Brisbane, Australia. It queries ipapi.co and weather providers Open-Meteo, wttr.in and met.no.
- Clipboard and other click actions reference `~/.config/rofi/scripts/`; install the included `rofi/` files at that path. The clipboard mode also references `~/.local/bin/rofi-clipboard`.
- The Quick Menu inherits the Rofi theme (`rofi/mytheme.rasi` in this repository). Its prompt font/padding override is contained in `scripts/quick-controls-rofi.sh`.
- The power menu includes shutdown/reboot and a Hyprland Lua logout command. Review `scripts/quick-controls-power.sh` for your compositor before using it.
- Tailscale's click action opens its local service address, `http://100.100.100.100`.

## Responsive monitor layouts

Launch `scripts/responsive-waybar.py` with Python 3 from Hyprland autostart. It runs Waybar, checks monitor layout every two seconds, and reloads only when the generated layout changes. A lock prevents duplicate responsive launchers. Shared module settings remain in `config-shared.jsonc`; generated per-monitor overrides live in `$XDG_RUNTIME_DIR/waybar-responsive/config.json`.

Thresholds use logical width (after rotation and scaling), not raw panel resolution:

| Width | Layout |
| --- | --- |
| 2000 px and wider | Full bar including music |
| Below 2000 px | Hide the music player first |
| Below 1400 px | Also hide network traffic and reduce spacing |
| Below 1100 px | Also hide weather, clipboard and screenshot buttons; allow clock to shift |
| Below 900 px | Also hide Tailscale; keep CPU, RAM and GPU gauges |

Workspaces, clock, volume and Quick Menu remain available. Adjust thresholds in `scripts/responsive-waybar.py`. `python3 scripts/responsive-waybar.py --print-config` previews the generated layout without starting Waybar.

## Network menu

The Quick Menu opens to the power tab; select the network tab for network controls. It displays wired connections and, when NetworkManager exposes a Wi-Fi adapter, nearby wireless networks. The connected Wi-Fi network is listed before other networks, which are sorted by signal strength.

Saved profiles are reused. New personal Wi-Fi connections use a masked Rofi password prompt and pass credentials to libnm in memory; the script does not put passwords in shell arguments or write its own password files. NetworkManager manages saved connection profiles. Hidden networks, enterprise authentication and other advanced setup remain available through the full network menu and Connection Editor.

The tab also provides refresh, Wi-Fi radio and disconnect actions. No wireless networks can be listed until the operating system and NetworkManager recognize a working Wi-Fi adapter.

## Files

- `config.jsonc`: monitor layouts.
- `config-shared.jsonc`: shared modules and actions.
- `style.css`: bar, tooltip text colours and hover styling.
- `usage-wheels.css`, `icons/`: gauge backgrounds and icons.
- `scripts/`: live metrics, menus and desktop actions. Some older text-based metric scripts are retained but are no longer used by the main layout.
- `tests/`: simulated Wi-Fi menu and connection-flow tests.
- `rofi/`: launcher configuration, themes, favourites and clipboard/screenshot/package/power menus.
- `bin/`: clipboard thumbnail helper and launcher toggle for `~/.local/bin`.

CSS changes reload automatically. Restart Waybar after changing its JSON configuration or a continuously running Python script. Reopen Rofi after menu changes.

## Checks

```sh
python3 -m unittest discover -s tests -v
for script in scripts/*.sh rofi/scripts/*.sh bin/*; do bash -n "$script"; done
```

The Wi-Fi tests use simulated NetworkManager devices and do not connect, disconnect or toggle any radios. Live behaviour still depends on your desktop services, hardware and installed fonts.

## Icon attribution

Tailscale icon attribution and the original media-kit location are recorded in `icons/tailscale-source.txt`. Tailscale branding remains the property of its owner. Nerd Font glyphs are rendered from your installed fonts and are not bundled font files.
