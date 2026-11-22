#!/usr/bin/env bash

set -u

find_tool() {
  for base in "${HASHCRACK_HOME:-}" /usr/share/hashcrack \
              "$HOME/.local/share/hashcrack"; do
    [ -n "$base" ] || continue
    if [ -f "$base/hashcrack.py" ]; then
      printf '%s\n' "$base/hashcrack.py"
      return 0
    fi
  done
  local self_dir
  self_dir="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
  [ -f "$self_dir/hashcrack.py" ] && printf '%s\n' "$self_dir/hashcrack.py"
}

TOOL="$(find_tool)"
if [ -z "$TOOL" ]; then
  echo "hashcrack: hashcrack.py not found." >&2
  echo "  Looked in /usr/share/hashcrack, ~/.local/share/hashcrack," >&2
  echo "  \$HASHCRACK_HOME and the launcher's own folder." >&2
  echo "  Re-install with:  sudo bash install-linux.sh" >&2
  [ -t 0 ] && { printf '\nPress Enter to close...'; read -r _; }
  exit 1
fi

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "hashcrack: python3 (>= 3.8) is required." >&2
  echo "  install:  sudo apt install python3" >&2
  [ -t 0 ] && { printf '\nPress Enter to close...'; read -r _; }
  exit 1
fi

"$PY" "$TOOL" "$@"
status=$?

if [ "${HASHCRACK_PAUSE:-0}" = "1" ] && [ -t 0 ]; then
  printf '\nPress Enter to close...'
  read -r _ || true
fi
exit $status
