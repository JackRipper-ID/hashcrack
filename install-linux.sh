#!/usr/bin/env bash
# ============================================================
#  hashcrack - installer for Kali / Debian / Ubuntu / Parrot
#  Usage:  sudo bash install-linux.sh
# ============================================================
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

# 1. detect package manager
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

# 2. base packages
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

# 3. verify modules, fallback to pip
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

# 4. install the tool
step "Installing hashcrack"
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ ! -f "$SRC/hashcrack.py" ]; then
  err "hashcrack.py not found in $SRC"
  exit 1
fi

if [ -w /usr/local/bin ] 2>/dev/null || [ "$(id -u)" = "0" ]; then
  cp "$SRC/hashcrack.py" /usr/local/bin/hashcrack
  chmod +x /usr/local/bin/hashcrack
  ok "installed as system command: hashcrack"
else
  mkdir -p "$HOME/.local/bin"
  cp "$SRC/hashcrack.py" "$HOME/.local/bin/hashcrack"
  chmod +x "$HOME/.local/bin/hashcrack"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) warn "add to PATH: echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
  esac
  ok "installed to ~/.local/bin/hashcrack"
fi

# 5. wordlist folder
step "Preparing ~/wordlists"
mkdir -p "$HOME/wordlists"
ok "folder ready - drop any .txt wordlist there"
[ -f /usr/share/wordlists/rockyou.txt ] && ok "Kali rockyou.txt detected (auto-include)"

# 6. summary
say ""
say "${C}  ---------------------------------------------${R}"
say "${G}${B}  Done!${R}"
say ""
say "  Run:        ${C}${B}hashcrack${R}"
say "  Test:       hashcrack --identify -H '<hash>'"
say "  Crack:      hashcrack -H <hash> -w wordlist.txt"
say ""
