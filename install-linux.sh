#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  hashcrack — installer for Kali / Debian / Ubuntu / Parrot / any distro
#  Usage:  sudo bash install-linux.sh
# ═══════════════════════════════════════════════════════════════════
set -u

RED=$'\033[91m'; GREEN=$'\\033[92m'; YELLOW=$'\\033[93m'
CYAN=$'\\033[96m'; GREY=$'\\033[90m'; BOLD=$'\\033[1m'; RST=$'\\033[0m'

ok()   { printf "%s✔%s %s\\n" "$GREEN" "$RST" "$*"; }
warn() { printf "%s!%s %s\\n" "$YELLOW" "$RST" "$*"; }
err()  { printf "%s✘%s %s\\n" "$RED" "$RST" "$*"; }
step() { printf "\\n%s▸%s %s%s%s\\n" "$CYAN" "$RST" "$BOLD" "$*" "$RST"; }

say ""
say "${BOLD}${CYAN}  ⚡ HASHCRACK by JackRipper-ID — Linux installer${RST}"
say "${GREY}  ────────────────────────────────────────────────${RST}"

if [ "$(id -u)" != "0" ]; then
  warn "Not root — some steps need sudo. Re-run with: sudo bash $0"
fi

# ── 1. detect distro / package manager ──
step "Detecting package manager"
if command -v apt >/dev/null 2>&1; then
  PKG="apt"; PKGINS="apt install -y"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"; PKGINS="dnf install -y"
elif command -v pacman >/dev/null 2>&1; then
  PKG="pacman"; PKGINS="pacman -S --noconfirm"
elif command -v zypper >/dev/null 2>&1; then
  PKG="zypper"; PKGINS="zypper install -y"
else
  err "No supported package manager found (apt/dnf/pacman/zypper)."
  say "  Install manually: python3, p7zip, python3-bcrypt, python3-passlib"
  exit 1
fi
ok "package manager: $PKG"

# ── 2. base packages ──
step "Installing base packages (python3, p7zip)"
case "$PKG" in
  apt)
    apt-get update -qq >/dev/null 2>&1 || true
    $PKGINS python3 python3-bcrypt python3-passlib p7zip-full >/dev/null 2>&1 \
      && ok "python3 + bcrypt + passlib + p7zip" \
      || warn "some packages failed — try: apt install python3-bcrypt python3-passlib p7zip-full"
    ;;
  dnf)
    $PKGINS python3 python3-bcrypt python3-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via dnf" || warn "check: dnf install python3-bcrypt python3-passlib p7zip"
    ;;
  pacman)
    $PKGINS python python-bcrypt python-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via pacman" || warn "check: pacman -S python-bcrypt python-passlib p7zip"
    ;;
  zypper)
    $PKGINS python3 python3-bcrypt python3-passlib p7zip >/dev/null 2>&1 \
      && ok "installed via zypper" || warn "check: zypper install python3-bcrypt python3-passlib p7zip"
    ;;
esac

# ── 3. fallback: pip if distro packages missing ──
step "Verifying python modules"
MISSING=0
python3 -c "import bcrypt" 2>/dev/null || MISSING=1
python3 -c "import passlib" 2>/dev/null || MISSING=1
if [ "$MISSING" = "1" ]; then
  warn "modules missing — trying pip"
  python3 -m pip install --quiet bcrypt passlib 2>/dev/null \
    && ok "installed via pip" \
    || { err "pip failed too. Run manually:"; say "    ${GREY}pip install bcrypt passlib${RST}"; }
else
  ok "bcrypt & passlib ready"
fi

# ── 4. install the tool ──
step "Installing hashcrack"
SRC="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SRC/hashcrack.py" ] || { err "hashcrack.py not found in $SRC"; exit 1; }

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
    *) warn "add ~/.local/bin to PATH: echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
  esac
  ok "installed to ~/.local/bin/hashcrack"
fi

# ── 5. wordlist folder ──
step "Preparing ~/wordlists"
mkdir -p "$HOME/wordlists"
ok "folder ready — drop any .txt wordlist there"
# Kali's rockyou auto-detected
[ -f /usr/share/wordlists/rockyou.txt ] && ok "Kali rockyou.txt detected (auto-include)"

# ── 6. summary ──
say ""
say "${GREY}  ────────────────────────────────────────────────${RST}"
say "${BOLD}${GREEN}  Done!${RST}"
say ""
say "  Run:        ${BOLD}${CYAN}hashcrack${RST}"
say "  Or:         ${GREY}python3 $(dirname "$SRC")/hashcrack.py${RST}"
say ""
say "  ${GREY}Quick test:${RST}"
say "  ${GREY}hashcrack -H \$(python3 -c \"import hashlib;print(hashlib.md5(b'rahasia').hexdigest())\") --literal rahasia${RST}"
say ""
