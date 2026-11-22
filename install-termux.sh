#!/usr/bin/env bash
set -u

G=$'\033[92m'; Y=$'\033[93m'; C=$'\033[96m'; R=$'\033[0m'; B=$'\033[1m'

say()   { printf "%s\n" "$*"; }
ok()    { printf "${G}[+]${R} %s\n" "$*"; }
warn()  { printf "${Y}[!]${R} %s\n" "$*"; }
err()   { printf "\033[91m[x]${R} %s\n" "$*"; }
step()  { printf "\n${C}>>>${R} ${B}%s${R}\n" "$*"; }

say ""
say "${C}${B}  HASHCRACK by JackRipper-ID - Termux installer${R}"

if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux" ]; then
  warn "This does not look like Termux, continuing anyway."
fi
if ! command -v pkg >/dev/null 2>&1; then
  err "'pkg' not found - this script is for Termux."
  say "  On a Linux desktop use: pip install bcrypt passlib"
  exit 1
fi

ARCH=$(uname -m)
step "Architecture: $ARCH"

step "Installing base packages (python, p7zip)"
pkg update -y >/dev/null 2>&1 || warn "pkg update failed, continuing"
pkg install -y python p7zip >/dev/null 2>&1 && ok "python and p7zip ready" \
  || warn "some packages failed, try manually: pkg install python p7zip"

step "Installing python modules (bcrypt, passlib)"
python -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true

install_mod() {
  local mod="$1"
  if python -c "import $mod" 2>/dev/null; then
    ok "$mod already installed"
    return 0
  fi
  if python -m pip install --quiet "$mod" 2>/dev/null; then
    ok "$mod installed (pip)"
  elif python -m pip install --quiet --no-cache-dir --no-binary :all: "$mod" 2>/dev/null; then
    ok "$mod installed (built from source)"
  else
    warn "$mod failed with pip, trying Termux package: python-$mod"
    if pkg install -y "python-$mod" >/dev/null 2>&1; then
      ok "$mod installed (pkg)"
    else
      err "$mod NOT installed - these formats will not work:"
      say "    python -m pip install $mod"
      return 1
    fi
  fi
}

install_mod bcrypt
install_mod passlib

step "Installing hashcrack.py"
DEST="$HOME/hashcrack"
mkdir -p "$DEST"
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SRC/hashcrack.py" ]; then
  cp "$SRC/hashcrack.py" "$DEST/hashcrack.py"
else
  err "hashcrack.py not found in $SRC"
  exit 1
fi
chmod +x "$DEST/hashcrack.py"
ok "tool installed at $DEST/hashcrack.py"

step "Creating the 'hashcrack' command"
LAUNCHER="$PREFIX/bin/hashcrack"
mkdir -p "$PREFIX/bin"
cat > "$LAUNCHER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$DEST/hashcrack.py" "\$@"
EOF
chmod +x "$LAUNCHER"
ok "run from anywhere: hashcrack"

step "Preparing the wordlist folder"
WL="$HOME/wordlists"
mkdir -p "$WL"
if [ ! -f "$WL/top1m.txt" ]; then
  say "  top-1-million password list is missing."
  read -r -p "  Download now? (~8 MB) [y/N]: " yn
  case "${yn:-n}" in
    [yY]*)
      URL="https://weakpass.com/download/50/10_million_password_list_top_1000000.txt.gz"
      if command -v curl >/dev/null 2>&1; then
        if curl -L --max-time 180 "$URL" -o "$WL/top1m.txt.gz" 2>/dev/null; then
          gunzip -f "$WL/top1m.txt.gz" 2>/dev/null && ok "top1m.txt ready ($(wc -l < "$WL/top1m.txt") lines)"
        else
          warn "download failed - you can add the file manually later"
        fi
      else
        warn "curl not found. Run: pkg install curl"
      fi
      ;;
    *) say "  skipped - put your own file in ~/wordlists/" ;;
  esac
else
  ok "top1m.txt already present in $WL"
fi

say ""
say "${G}${B}  Done${R}"
say ""
say "  Run:       ${C}${B}hashcrack${R}"
say "  Or:        python ~/hashcrack/hashcrack.py"
say ""
say "  Wordlists: ~/wordlists/"
say "  Quick test:"
say "    hashcrack -H \$(python -c \"import hashlib;print(hashlib.md5(b'test').hexdigest())\") -w ~/wordlists/top1m.txt"
say ""
say "  Termux notes:"
say "  - run termux-wake-lock so the crack is not frozen when the screen turns off"
say "  - the phone gets hot and drains the battery fast - keep it on the charger"
say "  - bcrypt on a phone is roughly 5-15 H/s, a 1M wordlist can take days"
say ""
