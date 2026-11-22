#!/usr/bin/env bash
set -u

RED=$'\033[91m'; GREEN=$'\033[92m'; YELLOW=$'\033[93m'
CYAN=$'\033[96m'; GREY=$'\033[90m'; BOLD=$'\033[1m'; RST=$'\033[0m'

say()  { printf "%s\n" "$*"; }
ok()   { printf "%s✔%s %s\n" "$GREEN" "$RST" "$*"; }
warn() { printf "%s!%s %s\n" "$YELLOW" "$RST" "$*"; }
err()  { printf "%s✘%s %s\n" "$RED" "$RST" "$*"; }
step() { printf "\n%s▸%s %s%s%s\n" "$CYAN" "$RST" "$BOLD" "$*" "$RST"; }

say ""
say "${BOLD}${CYAN}  ⚡ HASHCRACK — pemasangan untuk Termux${RST}"
say "${GREY}  ─────────────────────────────────────────${RST}"

if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux" ]; then
  warn "Ini sepertinya bukan Termux (tapi tetap bisa dicoba)."
fi
if ! command -v pkg >/dev/null 2>&1; then
  err "'pkg' tidak ditemukan — script ini untuk Termux."
  say "  Di Linux desktop cukup: pip install bcrypt passlib"
  exit 1
fi

ARCH=$(uname -m)
step "Arsitektur: $ARCH"

step "Memasang paket dasar (python, p7zip)"
pkg update -y >/dev/null 2>&1 || warn "pkg update gagal, lanjut saja"
pkg install -y python p7zip >/dev/null 2>&1 && ok "python & p7zip siap" \
  || warn "sebagian paket gagal dipasang, coba manual: pkg install python p7zip"

step "Memasang modul Python (bcrypt, passlib)"
python -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true

install_mod() {
  local mod="$1"
  if python -c "import $mod" 2>/dev/null; then
    ok "$mod sudah ada"
    return 0
  fi
  if python -m pip install --quiet "$mod" 2>/dev/null; then
    ok "$mod terpasang (pip)"
  elif python -m pip install --quiet --no-cache-dir --no-binary :all: "$mod" 2>/dev/null; then
    ok "$mod terpasang (build source)"
  else
    warn "$mod gagal lewat pip, mencoba paket Termux: python-$mod"
    if pkg install -y "python-$mod" >/dev/null 2>&1; then
      ok "$mod terpasang (pkg)"
    else
      err "$mod TIDAK terpasang — format terkait tidak akan bekerja:"
      say "    ${GREY}python -m pip install $mod${RST}"
      return 1
    fi
  fi
}

install_mod bcrypt
install_mod passlib

step "Memasang hashcrack.py"
DEST="$HOME/hashcrack"
mkdir -p "$DEST"
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SRC/hashcrack.py" ]; then
  cp "$SRC/hashcrack.py" "$DEST/hashcrack.py"
else
  err "hashcrack.py tidak ditemukan di $SRC"
  exit 1
fi
chmod +x "$DEST/hashcrack.py"
ok "tool dipasang di $DEST/hashcrack.py"

step "Membuat perintah 'hashcrack'"
LAUNCHER="$PREFIX/bin/hashcrack"
mkdir -p "$PREFIX/bin"
cat > "$LAUNCHER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
exec python "$DEST/hashcrack.py" "\$@"
EOF
chmod +x "$LAUNCHER"
ok "sekarang bisa dijalankan dari mana saja: $BOLD$hashcrack$RST"

step "Menyiapkan folder wordlist"
WL="$HOME/wordlists"
mkdir -p "$WL"
if [ ! -f "$WL/top1m.txt" ]; then
  say "  Wordlist top-1-juta password tidak ada."
  read -r -p "  Unduh sekarang? (~8 MB) [y/N]: " yn
  case "${yn:-n}" in
    [yY]*)
      URL="https://weakpass.com/download/50/10_million_password_list_top_1000000.txt.gz"
      if command -v curl >/dev/null 2>&1; then
        if curl -L --max-time 180 "$URL" -o "$WL/top1m.txt.gz" 2>/dev/null; then
          gunzip -f "$WL/top1m.txt.gz" 2>/dev/null && ok "top1m.txt siap ($(wc -l < "$WL/top1m.txt") baris)"
        else
          warn "unduhan gagal — bisa ditaruh manual nanti"
        fi
      else
        warn "curl tidak ada. Jalankan: pkg install curl"
      fi
      ;;
    *) say "  dilewati — taruh file sendiri di ~/wordlists/" ;;
  esac
else
  ok "top1m.txt sudah ada di $WL"
fi

say ""
say "${GREY}  ─────────────────────────────────────────${RST}"
say "${BOLD}${GREEN}  Selesai!${RST}"
say ""
say "  Jalankan:  ${BOLD}${CYAN}hashcrack${RST}"
say "  Atau:      ${GREY}python ~/hashcrack/hashcrack.py${RST}"
say ""
say "  ${GREY}Wordlist ada di ~/wordlists/"
say "  Test cepat:${RST}"
say "    ${GREY}hashcrack -H \$(python -c \"import hashlib;print(hashlib.md5(b'rahasia').hexdigest())\") -w ~/wordlists/top1m.txt${RST}"
say ""
say "  ${YELLOW}Catatan Termux:${RST}"
say "  ${GREY}• tambahkan termux-wake-lock agar crack tidak putus saat layar mati${RST}"
say "  ${GREY}• HP akan panas & baterai turun cepat — colok charger${RST}"
say "  ${GREY}• bcrypt di HP ≈ 5–15 H/s, kamus 1 juta bisa berhari-hari${RST}"
say ""
