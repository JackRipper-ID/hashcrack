#!/usr/bin/env bash
set -u

G='\033[92m'; Y='\033[93m'; C='\033[96m'; R='\033[0m'; B='\033[1m'

say()   { printf "%b\n" "$*"; }
ok()    { printf "${G}[+]${R} %s\n" "$*"; }
warn()  { printf "${Y}[!]${R} %s\n" "$*"; }
err()   { printf "\033[91m[x]${R} %s\n" "$*"; }
step()  { printf "\n${C}>>>${R} ${B}%s${R}\n" "$*"; }

say ""
say "${C}${B}  HASHCRACK by JackRipper-ID - Linux installer${R}"
say "${C}  ---------------------------------------------${R}"

if [ "$(id -u)" != "0" ]; then
  warn "Not root - re-run with: sudo bash $0"
fi

step "Detecting package manager"
if command -v apt >/dev/null 2>&1; then
  PKG="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PKG="pacman"
elif command -v zypper >/dev/null 2>&1; then
  PKG="zypper"
else
  err "No supported package manager (apt/dnf/pacman/zypper)."
  say "  Install manually: python3, p7zip, python3-bcrypt, python3-passlib"
  exit 1
fi
ok "package manager: $PKG"

step "Installing base packages (python3, bcrypt, passlib, p7zip)"
case "$PKG" in
  apt)
    apt-get update -qq >/dev/null 2>&1 || true
    apt install -y python3 python3-bcrypt python3-passlib p7zip-full >/dev/null 2>&1 \
      && ok "python3 + bcrypt + passlib + p7zip installed" \
      || warn "partial failure - run: apt install python3-bcrypt python3-passlib p7zip-full"
    ;;
  dnf)
    dnf install -y python3 python3-bcrypt python3-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via dnf" || warn "check: dnf install python3-bcrypt python3-passlib p7zip"
    ;;
  pacman)
    pacman -S --noconfirm python python-bcrypt python-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via pacman" || warn "check: pacman -S python-bcrypt python-passlib p7zip"
    ;;
  zypper)
    zypper install -y python3 python3-bcrypt python3-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via zypper" || warn "check: zypper install python3-bcrypt python3-passlib p7zip"
    ;;
esac

step "Verifying python modules"
MISSING=0
python3 -c "import bcrypt" 2>/dev/null || MISSING=1
python3 -c "import passlib" 2>/dev/null || MISSING=1
if [ "$MISSING" = "1" ]; then
  warn "modules missing - trying pip"
  python3 -m pip install --quiet bcrypt passlib 2>/dev/null \
    && ok "installed via pip" \
    || { err "pip failed too. Run manually:"; say "    pip install bcrypt passlib"; }
else
  ok "bcrypt & passlib ready"
fi

step "Installing hashcrack"
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$SRC/hashcrack.py" ]; then
  err "hashcrack.py not found in $SRC"
  exit 1
fi

if [ -w /usr/local/bin ] 2>/dev/null || [ "$(id -u)" = "0" ]; then
  BIN=/usr/local/bin
  SHARE=/usr/share
  ICONDIR=/usr/share/icons/hicolor/256x256/apps
  APPDIR=/usr/share/applications
else
  BIN="$HOME/.local/bin"
  SHARE="$HOME/.local/share"
  ICONDIR="$HOME/.local/share/icons/hicolor/256x256/apps"
  APPDIR="$HOME/.local/share/applications"
fi

mkdir -p "$BIN" "$SHARE/hashcrack" "$ICONDIR" "$APPDIR"
cp "$SRC/hashcrack.py" "$SHARE/hashcrack/hashcrack.py"
chmod +x "$SHARE/hashcrack/hashcrack.py"

if [ -f "$SRC/hashcrack.sh" ]; then
  cp "$SRC/hashcrack.sh" "$BIN/hashcrack"
else
  cat > "$BIN/hashcrack" <<'LAUNCH'
#!/usr/bin/env bash
set -u
for base in /usr/share/hashcrack "$HOME/.local/share/hashcrack"; do
  [ -f "$base/hashcrack.py" ] && exec python3 "$base/hashcrack.py" "$@"
done
self_dir="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
[ -f "$self_dir/hashcrack.py" ] && exec python3 "$self_dir/hashcrack.py" "$@"
echo "hashcrack: hashcrack.py not found. Re-install: sudo bash install-linux.sh" >&2
[ -t 0 ] && { printf '\nPress Enter to close...'; read -r _; }
exit 1
LAUNCH
fi
chmod +x "$BIN/hashcrack"
ok "command installed: hashcrack"

cp "$SRC/hashcrack.py" /dev/null 2>/dev/null || true
if [ -f "$SRC/packaging/hashcrack.desktop" ]; then
  sed -e "s|^Icon=.*|Icon=hashcrack|" \
      -e "s|^Exec=.*|Exec=env HASHCRACK_PAUSE=1 $BIN/hashcrack|" \
      -e "s|^TryExec=.*|TryExec=$BIN/hashcrack|" \
      "$SRC/packaging/hashcrack.desktop" > "$APPDIR/hashcrack.desktop"
  chmod 644 "$APPDIR/hashcrack.desktop"
fi
if [ -f "$SRC/assets/icon-256.png" ]; then
  cp "$SRC/assets/icon-256.png" "$ICONDIR/hashcrack.png"
elif [ -f "$SRC/hashcrack.png" ]; then
  cp "$SRC/hashcrack.png" "$ICONDIR/hashcrack.png"
fi
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$APPDIR" 2>/dev/null
command -v gtk-update-icon-cache   >/dev/null 2>&1 && gtk-update-icon-cache -qtf "$(
  [ -d /usr/share/icons/hicolor ] && echo /usr/share/icons/hicolor || echo "$HOME/.local/share/icons/hicolor")" 2>/dev/null
ok "menu entry + icon installed (app launcher: HASHCRACK)"

step "Preparing ~/wordlists"
mkdir -p "$HOME/wordlists"
ok "folder ready - drop any .txt wordlist there"
[ -f /usr/share/wordlists/rockyou.txt ] && ok "Kali rockyou.txt detected (auto-include)"

say ""
say "${C}  ---------------------------------------------${R}"
say "${G}${B}  Done!${R}"
say ""
say "  Terminal:   ${C}${B}hashcrack${R}"
say "  App menu:   ${B}HASHCRACK${R} (opens a terminal window automatically)"
say "  Test:       hashcrack --identify -H '<hash>'"
say "  Crack:      hashcrack -H <hash> -w wordlist.txt"
say ""
