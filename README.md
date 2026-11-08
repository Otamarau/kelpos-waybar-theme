# Waybar

Personal Waybar and Rofi configuration for Arch Linux and Hyprland, with compact hardware gauges, a recent-app launcher, and tabbed controls for Wi-Fi, Bluetooth, packages and power.

![Waybar preview with workspaces, weather, network traffic, clock, media controls and hardware gauges](images/Pasted%20image.png)

## Features

- White CPU, RAM, swap, GPU and VRAM usage wheels with detailed tooltips.
- Per-thread CPU usage and compact per-core temperature tables.
- Colour-coded CPU/GPU temperatures.
- Fixed-width download/upload readings that dim when idle.
- Scrolling MPRIS media titles, album art, playback controls and Cava visualizers.
- Rofi app launcher, window switcher, clipboard history with image previews, calculator and screenshot tools.
- Tabbed Rofi Quick Menu with a Wi-Fi picker, Ethernet status, Bluetooth controls, repository/AUR package browser and power actions.
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
install -m 755 bin/rofi-clipboard bin/rofi-toggle.sh bin/rofi-recent bin/rofi-record-launch ~/.local/bin/
bash scripts/install-window-icons.sh
```

Rofi uses the installed Adwaita theme and application icons from hicolor. The icon setup script adds aliases for VS Code and Monero because the Wayland window switcher looks up lowercase window application IDs.

Launch with `~/.local/bin/rofi-recent`, or use `~/.local/bin/rofi-toggle.sh` as a keyboard shortcut. The Quick Menu remains at `~/.config/waybar/scripts/quick-controls-rofi.sh`.

The app launcher lists recently launched apps first when the search is empty. Typing searches app names with fuzzy matching and ranks results by match quality. Launches through this wrapper are recorded in `$XDG_STATE_HOME/rofi/recent-apps.json` (default `~/.local/state/rofi/recent-apps.json`). Existing Rofi history supplies the initial order; launches outside this wrapper are not tracked.

For Hyprland, use these bindings (replace existing bindings for the same keys):

```ini
bind = SUPER, SPACE, exec, ~/.local/bin/rofi-toggle.sh
bind = SUPER, R, exec, ~/.local/bin/rofi-recent
```

This setup targets Rofi 2.0. Its `drun.DBusActivatable` option is disabled so applications such as GNOME Files use their desktop entry's command and pass through the recorder. The recorder uses GIO to identify desktop entries on builds that do not export `DESKTOP_ENTRY_ID`. Personal launch history is not included in the repository.

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
| Rofi recent-app tracking | Python 3, PyGObject (`python-gobject` on Arch), GIO introspection |
| Quick Menu package browser | pacman, yay (AUR and combined searches), sudo (repository installs), Kitty, Python 3, notify-send |
| Standalone package menu | yay, Kitty; launch `~/.config/rofi/scripts/pkgmanager.sh` separately for Install / Remove / Info |
| Weather | curl, jq (preferred), gnome-weather for the click action |
| Other click actions | missioncenter, gsimplecal, tailscale, hyprctl, hyprlock |

Install the dependencies for the features you use, or remove those modules from the layout.

### Machine-specific settings

- The responsive launcher reads Hyprland monitor sizes, rotation and scale. `config.jsonc` remains a static fallback for launching Waybar directly.
- GPU gauges currently require AMD-style `gpu_busy_percent` and VRAM counters in `/sys/class/drm`.
- The RAM tooltip reads firmware-configured speed in MT/s from `udevadm` once at startup, without root access. If firmware/udev does not expose it, the speed is shown as unavailable.
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

## Rofi launcher and Quick Menu

The included Rofi setup has two entry points: the app launcher for everyday desktop tasks and the Quick Menu for system controls. Both use the shared theme and icon tabs; switch tabs with **Left / Right** or click their icons.

### App launcher

Open `~/.local/bin/rofi-recent`, or use **Super + Space** after installing the bindings above. The toggle shortcut closes an already-open Rofi menu; clicking outside also dismisses it.

| Tab | Features |
| --- | --- |
| Applications | Application icons, recently launched apps first with an empty search, and fuzzy app-name search ranked by match quality. Launch history is tracked by the included wrapper. |
| Windows | Find and switch to an open window, with application icons. |
| Clipboard | Search saved text and image entries from cliphist. Images have cached thumbnail previews; selecting an entry copies the original text or full image back to the clipboard. |
| Screenshots | Capture a selected area or the full desktop, save a timestamped PNG under `~/Pictures/Screenshots`, copy it to the clipboard and show a notification. |
| Calculator | Evaluate expressions with the Rofi calc plugin and copy the accepted result to the clipboard. |

Waybar also provides direct clipboard and screenshot buttons. Left-click the screenshot button for an area capture; right-click for a full-desktop capture.

### Quick Menu

Open the Quick Menu from Waybar or run:

```sh
~/.config/waybar/scripts/quick-controls-rofi.sh
```

It starts on the **Power** tab, with **Network**, **Bluetooth** and **Packages** available alongside it.

### Wi-Fi picker and Ethernet

- Browse nearby Wi-Fi networks with signal percentages, signal-strength icons, open/secured indicators and a connected marker. The current network comes first, followed by other networks sorted by signal strength.
- Select a network to connect. Saved profiles are reused; new personal Wi-Fi connections open a masked password prompt.
- Refresh the network list, turn the Wi-Fi radio on or off, or disconnect an active wireless connection.
- View Ethernet interfaces, profile names and connection status; select a wired entry to open Connection Editor.
- Open the full network menu for hidden networks and advanced setup, or launch Connection Editor directly.

Passwords are passed to libnm in memory, rather than shell arguments or script-created password files. NetworkManager manages saved profiles. Enterprise authentication and other advanced connection setup use the external network tools. Wireless discovery requires a Wi-Fi adapter recognized by NetworkManager; the menu also reports unavailable adapters and hardware radio blocks.

### Package browser

The **Packages** tab searches **official repositories**, the **AUR**, or **both**. Choose a source, type at least two characters of a package name or description, and press **Enter**.

- Results show the package name, repository, version, description, application icon when available, and a checkmark for installed packages.
- Exact names rank first, with application matches ahead of language packs and add-ons. Results are limited to the first 100 matches; narrow the query for more specific results.
- Select a package to inspect details such as its description, version, URL, dependencies, download/installed sizes and AUR votes when supplied by the package source.
- Choose **Install in terminal** to open Kitty with an interactive installation: `sudo pacman` for repository packages or `yay` for AUR packages. Normal authentication and package-manager prompts remain visible.
- Return to results, start a new search or change source from within the menu. Loading notifications provide feedback during searches and detail retrieval.

Package icons use local icons where available, with cached Papirus downloads for missing matches. The older standalone `~/.config/rofi/scripts/pkgmanager.sh` offers **Install / Remove / Info** through yay; removal is available there, not in the Quick Menu package browser.

### Bluetooth

Enable or disable Bluetooth, refresh the known-device list, and select a device to connect or disconnect. Filled and empty circles indicate connection state. **Open Overskride** launches the full Bluetooth manager for discovery, pairing and PIN/confirmation workflows. The inline menu reports connection failures and unavailable adapters or services.

### Power

**Power Off**, **Reboot**, **Logout** and **Lock** are available in the Power tab. Logout uses the Hyprland Lua exit dispatcher, and Lock launches Hyprlock directly. Power actions execute when selected, without a separate confirmation menu.

## Files

- `config.jsonc`: monitor layouts.
- `config-shared.jsonc`: shared modules and actions.
- `style.css`: bar, tooltip text colours and hover styling.
- `usage-wheels.css`, `icons/`: gauge backgrounds and icons.
- `scripts/`: live metrics, menus and desktop actions. Some older text-based metric scripts are retained but are no longer used by the main layout.
- `tests/`: checks for network, Bluetooth and package menus, recent-app tracking, responsive layouts and native helpers.
- `rofi/`: launcher configuration, themes, favourites and clipboard/screenshot/package/power menus.
- `bin/`: clipboard thumbnail helper, launcher toggle and recent-app tracking helpers for `~/.local/bin`.

CSS changes reload automatically. Restart Waybar after changing its JSON configuration or a continuously running Python script. Reopen Rofi after menu changes.

## Checks

```sh
python3 -m unittest discover -s tests -v
for script in scripts/*.sh rofi/scripts/*.sh bin/*.sh bin/rofi-clipboard; do bash -n "$script"; done
python3 -m py_compile bin/rofi-recent bin/rofi-record-launch
```

The Wi-Fi tests use simulated NetworkManager devices and do not connect, disconnect or toggle any radios. Live behaviour still depends on your desktop services, hardware and installed fonts.

## Icon attribution

Tailscale icon attribution and the original media-kit location are recorded in `icons/tailscale-source.txt`. Tailscale branding remains the property of its owner. Nerd Font glyphs are rendered from your installed fonts and are not bundled font files.
