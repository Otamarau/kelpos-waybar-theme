#!/usr/bin/env bash
# Follow the actual Rofi process, including keyboard launches and dismissals.
case "${1:-}" in
  arch) pattern=' -show drun ' ;;
  quickmenu) pattern=' -p Quick ' ;;
  *) exit 1 ;;
esac

previous_class=
while true; do
  menu_class=inactive
  while IFS= read -r process; do
    if [[ " $process " == *"$pattern"* ]]; then
      menu_class=active
      break
    fi
  done < <(pgrep -a -u "$UID" -x 'rofi|rofi-wayland' || true)

  # Avoid rewriting the tooltip while the menu state is unchanged.
  if [[ "$menu_class" != "$previous_class" ]]; then
    printf '{"text":"", "class":"%s"}\n' "$menu_class"
    previous_class=$menu_class
  fi
  [[ "${2:-}" == "--watch" ]] || break
  sleep 0.25
done
