# Waybar

Personal Waybar configuration for Arch Linux and Hyprland, with compact hardware gauges and a Rofi network menu.

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
waybar -c ~/.config/waybar/config.jsonc -s ~/.config/waybar/style.css
```

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
| Weather | curl, jq (preferred), gnome-weather for the click action |
| Other click actions | missioncenter, gsimplecal, tailscale, hyprctl, hyprlock |

Install the dependencies for the features you use, or remove those modules from the layout.

### Machine-specific settings

- `config.jsonc` uses `DP-2` for the second, portrait monitor. Change the output names to match your desktop.
- GPU gauges currently require AMD-style `gpu_busy_percent` and VRAM counters in `/sys/class/drm`.
- CPU temperatures support `coretemp`, `k10temp` and `zenpower` sensors. Temperature colours use the sensors' reported limits, with fallback display thresholds when limits are absent.
- The weather script uses IP geolocation, falling back to Brisbane, Australia. It queries ipapi.co and weather providers Open-Meteo, wttr.in and met.no.
- Clipboard and some legacy click actions reference scripts under `~/.config/rofi/scripts/`; those external scripts are not included here. Update the actions to your own launcher/clipboard setup.
- The Quick Menu inherits your existing Rofi theme. Its prompt font/padding override is contained in `scripts/quick-controls-rofi.sh`.
- The power menu includes shutdown/reboot and a Hyprland Lua logout command. Review `scripts/quick-controls-power.sh` for your compositor before using it.
- Tailscale's click action opens its local service address, `http://100.100.100.100`.

## Network menu

The Quick Menu opens to the network tab. It displays wired connections and, when NetworkManager exposes a Wi-Fi adapter, nearby wireless networks. The connected Wi-Fi network is listed before other networks, which are sorted by signal strength.

Saved profiles are reused. New personal Wi-Fi connections use a masked Rofi password prompt and pass credentials to libnm in memory; the script does not put passwords in shell arguments or write its own password files. NetworkManager manages saved connection profiles. Hidden networks, enterprise authentication and other advanced setup remain available through the full network menu and Connection Editor.

The tab also provides refresh, Wi-Fi radio and disconnect actions. No wireless networks can be listed until the operating system and NetworkManager recognize a working Wi-Fi adapter.

## Files

- `config.jsonc`: monitor layouts.
- `config-shared.jsonc`: shared modules and actions.
- `style.css`: bar, tooltip text colours and hover styling.
- `usage-wheels.css`, `icons/`: gauge backgrounds and icons.
- `scripts/`: live metrics, menus and desktop actions. Some older text-based metric scripts are retained but are no longer used by the main layout.
- `tests/`: simulated Wi-Fi menu and connection-flow tests.

CSS changes reload automatically. Restart Waybar after changing its JSON configuration or a continuously running Python script. Reopen Rofi after menu changes.

## Checks

```sh
python3 -m unittest discover -s tests -v
for script in scripts/*.sh; do bash -n "$script"; done
```

The Wi-Fi tests use simulated NetworkManager devices and do not connect, disconnect or toggle any radios. Live behaviour still depends on your desktop services, hardware and installed fonts.

## Icon attribution

Tailscale icon attribution and the original media-kit location are recorded in `icons/tailscale-source.txt`. Tailscale branding remains the property of its owner. Nerd Font glyphs are rendered from your installed fonts and are not bundled font files.
