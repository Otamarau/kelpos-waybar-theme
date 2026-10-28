#!/usr/bin/env python3
"""Show active MPRIS media and cache its cover for Waybar's image module."""

import fcntl
import html
import json
import os
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

import gi

gi.require_version("Playerctl", "2.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib, Playerctl


CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "waybar/now-playing"
MAX_ART_BYTES = 5 * 1024 * 1024
ART_SIZE = 256
TITLE_WIDTH = 22
# GTK needs 500ms without tooltip queries before displaying the first tooltip.
# Waybar rewrites tooltip markup on every custom-module update, even unchanged.
SCROLL_STEP_SECONDS = 1.0
SCROLL_PAUSE_SECONDS = 2


def active_player():
    """Prefer playing media, then Spotify when multiple players are tied."""
    candidates = []
    for name in Playerctl.list_players():
        if name.name == "playerctld":
            continue
        try:
            player = Playerctl.Player.new_from_name(name)
            metadata = player.props.metadata.unpack()
            status = player.props.status
            if status not in ("Playing", "Paused") or not metadata.get("xesam:title"):
                continue
            candidates.append((status != "Playing", name.name != "spotify", name.instance, player, metadata))
        except GLib.Error:
            # Players can disappear between discovery and metadata retrieval.
            continue
    if not candidates:
        return None, {}
    selected = min(candidates, key=lambda item: item[:3])
    return selected[3], selected[4]


def update_cover(url):
    """Keep one thumbnail; serialize updates from bars on multiple monitors."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cover = CACHE / "cover.png"
    state_file = CACHE / "art.json"
    with (CACHE / "art.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(state_file.read_text())
        except (OSError, ValueError):
            state = {}
        if state.get("url") == url and state.get("size") == ART_SIZE:
            if cover.exists() or time.time() - state.get("attempt", 0) < 60:
                return

        # Never leave the previous track's cover beside the new title.
        cover.unlink(missing_ok=True)
        state_file.write_text(json.dumps({"url": url, "attempt": time.time(), "size": ART_SIZE}))
        if not url:
            return
        temporary = CACHE / "cover.tmp.png"
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme == "file" and parsed.netloc in ("", "localhost"):
                with Path(urllib.request.url2pathname(parsed.path)).open("rb") as source:
                    data = source.read(MAX_ART_BYTES + 1)
            elif parsed.scheme in ("https", "http"):
                request = urllib.request.Request(url, headers={"User-Agent": "Waybar-NowPlaying/1.0"})
                with urllib.request.urlopen(request, timeout=3) as response:
                    data = response.read(MAX_ART_BYTES + 1)
            else:
                return
            if len(data) > MAX_ART_BYTES:
                return
            loader = GdkPixbuf.PixbufLoader.new()
            loader.set_size(ART_SIZE, ART_SIZE)
            loader.write(data)
            loader.close()
            loader.get_pixbuf().savev(str(temporary), "png", [], [])
            temporary.replace(cover)
        except (OSError, ValueError, GLib.Error):
            # Missing/offline artwork must not prevent the title from appearing.
            temporary.unlink(missing_ok=True)


def scrolling_title(title, elapsed):
    """Pan long titles back and forth, pausing at either end."""
    distance = len(title) - TITLE_WIDTH
    if distance <= 0:
        return title
    travel = distance * SCROLL_STEP_SECONDS
    phase = elapsed % (2 * (SCROLL_PAUSE_SECONDS + travel))
    if phase < SCROLL_PAUSE_SECONDS:
        offset = 0
    elif phase < SCROLL_PAUSE_SECONDS + travel:
        offset = min(distance, int((phase - SCROLL_PAUSE_SECONDS) / SCROLL_STEP_SECONDS))
    elif phase < 2 * SCROLL_PAUSE_SECONDS + travel:
        offset = distance
    else:
        offset = max(0, distance - int((phase - 2 * SCROLL_PAUSE_SECONDS - travel) / SCROLL_STEP_SECONDS))
    return title[offset:offset + TITLE_WIDTH]


def display(metadata, status, elapsed=None):
    if not metadata:
        return {"text": "", "tooltip": "", "class": "empty"}
    title = " ".join(metadata.get("xesam:title", "").split())
    artists = metadata.get("xesam:artist", [])
    artist = ", ".join(artists) if isinstance(artists, list) else str(artists)
    details = [title, artist, metadata.get("xesam:album", ""), status]
    tooltip = "\n".join(html.escape(value) for value in details if value)
    tooltip += "\n\nClick: play/pause · Right: next · Middle: previous"
    visible = scrolling_title(title, elapsed) if elapsed is not None else title
    return {"text": html.escape(visible), "tooltip": tooltip, "class": status.lower()}


def stream():
    """Keep scrolling state in memory; a new track starts at its beginning."""
    previous_key = None
    started = time.monotonic()
    next_poll = 0
    metadata, status = {}, ""
    while True:
        now = time.monotonic()
        if now >= next_poll:
            try:
                player, metadata = active_player()
                status = player.props.status if player else ""
                key = (player.props.player_name if player else None,
                       metadata.get('mpris:trackid'), metadata.get('xesam:title'))
                if key != previous_key:
                    started = now
                    previous_key = key
                update_cover(metadata.get('mpris:artUrl', ''))
            except GLib.Error:
                metadata, status = {}, ""
                previous_key = None
            next_poll = time.monotonic() + 1
        print(json.dumps(display(metadata, status, time.monotonic() - started)), flush=True)
        time.sleep(SCROLL_STEP_SECONDS)


def main():
    if sys.argv[1:] == ['--stream']:
        stream()
        return
    player, metadata = active_player()
    if len(sys.argv) == 3 and sys.argv[1] == "--control":
        if not player:
            result = {"text": "", "tooltip": "", "class": "empty"}
        elif sys.argv[2] == "play-pause":
            playing = player.props.status == "Playing"
            result = {"text": "" if playing else "",
                      "tooltip": "Pause" if playing else "Play",
                      "class": player.props.status.lower()}
        elif sys.argv[2] == "previous":
            result = {"text": "", "tooltip": "Previous track"}
        else:
            result = {"text": "", "tooltip": "Skip to next track"}
        print(json.dumps(result))
        return
    if len(sys.argv) > 1:
        actions = {"play-pause": "play_pause", "next": "next", "previous": "previous"}
        if player and sys.argv[1] in actions:
            getattr(player, actions[sys.argv[1]])()
        return
    update_cover(metadata.get("mpris:artUrl", ""))
    print(json.dumps(display(metadata, player.props.status if player else "")))


if __name__ == "__main__":
    try:
        main()
    except GLib.Error:
        print(json.dumps({"text": "", "class": "empty"}))
    except BrokenPipeError:
        pass
