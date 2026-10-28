#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
read -r -a gtk_flags <<< "$(pkg-config --cflags --libs gtk+-3.0)"
cc -shared -fPIC -O2 -Wall -Wextra -Werror \
  "$root/cffi/album-art.c" -o "$root/cffi/album-art.so" "${gtk_flags[@]}"
# Waybar passes module_path directly to dlopen, without expanding ~ or $HOME.
python3 - "$root" <<'PY'
import json
from pathlib import Path
import re
import sys
root = Path(sys.argv[1])
config = root / 'config-shared.jsonc'
text, count = re.subn(r'("cffi/album-art":\s*\{\s*"module_path":\s*)"[^"]*"',
                     lambda m: m[1] + json.dumps(str(root / 'cffi/album-art.so')),
                     config.read_text(), count=1)
if count != 1:
    raise SystemExit('Could not locate cffi/album-art module_path in config-shared.jsonc')
config.write_text(text)
PY
printf 'Built %s\n' "$root/cffi/album-art.so"
