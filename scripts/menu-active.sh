#!/usr/bin/env bash
# Follow the actual Rofi process, including keyboard launches and dismissals.
case "${1:-}" in
  arch) pattern=' -show drun ' ;;
  quickmenu) pattern=' -p Quick ' ;;
  *) exit 1 ;;
esac

menu_class=inactive
while IFS= read -r process; do
  if [[ " $process " == *"$pattern"* ]]; then
    menu_class=active
    break
  fi
done < <(pgrep -a -u "$UID" -x 'rofi|rofi-wayland' || true)

printf '{"text":"", "class":"%s"}\n' "$menu_class"
