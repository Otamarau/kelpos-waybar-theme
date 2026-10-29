#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
read -r -a gtk_flags <<< "$(pkg-config --cflags --libs gtk+-3.0)"
cc -shared -fPIC -O2 -Wall -Wextra -Werror \
  "$root/cffi/workspace-cursor.c" -o "$root/cffi/workspace-cursor.so" "${gtk_flags[@]}"
