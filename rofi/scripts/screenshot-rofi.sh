#!/usr/bin/env bash

case "${ROFI_RETV:-0}" in
    0)
        printf '%s\n' "Area screenshot" "Full-screen screenshot"
        ;;
    1)
        case "$1" in
            "Area screenshot")
                exec "$HOME/.config/waybar/scripts/screenshot-area.sh"
                ;;
            "Full-screen screenshot")
                exec "$HOME/.config/waybar/scripts/screenshot-full.sh"
                ;;
        esac
        ;;
esac
