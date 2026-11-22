#!/usr/bin/env bash
# Build distributable packages: .deb + .AppImage
# Requires: dpkg-deb, fakeroot, mksquashfs (squashfs-tools), python3
# Usage:  bash build-packages.sh
set -eu

VERSION="${VERSION:-1.0.0}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo ">>> preparing AppDir"
rm -rf packaging/appdir
mkdir -p packaging/appdir/usr/share/hashcrack \
         packaging/appdir/usr/share/applications \
         packaging/appdir/usr/share/icons/hicolor/256x256/apps
cp hashcrack.py packaging/appdir/usr/share/hashcrack/hashcrack.py
cp packaging/hashcrack.desktop packaging/appdir/hashcrack.desktop
cp packaging/hashcrack.desktop packaging/appdir/usr/share/applications/hashcrack.desktop
cp packaging/AppRun packaging/appdir/AppRun
cp assets/icon-256.png packaging/appdir/usr/share/icons/hicolor/256x256/apps/hashcrack.png
if [ ! -f packaging/appdir/AppRun ]; then
  echo "ERROR: packaging/appdir/AppRun missing"
  exit 1
fi
chmod +x packaging/appdir/AppRun
chmod -R a+rX packaging/appdir

if [ ! -f packaging/appdir_runtime ]; then
  echo ">>> fetching AppImage runtime"
  curl -sL -o packaging/appdir_runtime \
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
  chmod +x packaging/appdir_runtime
fi

if [ ! -x /tmp/appimagetool.AppImage ]; then
  echo ">>> fetching appimagetool"
  curl -sL -o /tmp/appimagetool.AppImage \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x /tmp/appimagetool.AppImage
fi

echo ">>> building AppImage"
ARCH=x86_64 /tmp/appimagetool.AppImage --runtime-file packaging/appdir_runtime \
  --comp zstd packaging/appdir "HASHCRACK-${VERSION}-x86_64.AppImage"
chmod +x "HASHCRACK-${VERSION}-x86_64.AppImage"

echo ">>> building .deb"
DEB=/tmp/hashcrack-deb
rm -rf "$DEB"
mkdir -p "$DEB/DEBIAN" "$DEB/usr/bin" "$DEB/usr/share/hashcrack" \
         "$DEB/usr/share/applications" "$DEB/usr/share/icons/hicolor/256x256/apps"
cp hashcrack.sh "$DEB/usr/bin/hashcrack"
cp hashcrack.py "$DEB/usr/share/hashcrack/hashcrack.py"
cp packaging/hashcrack.desktop "$DEB/usr/share/applications/hashcrack.desktop"
cp assets/icon-256.png "$DEB/usr/share/icons/hicolor/256x256/apps/hashcrack.png"
chmod 755 "$DEB/usr/bin/hashcrack" "$DEB/usr/share/hashcrack/hashcrack.py"
chmod 644 "$DEB/usr/share/applications/hashcrack.desktop" \
          "$DEB/usr/share/icons/hicolor/256x256/apps/hashcrack.png"

cat > "$DEB/DEBIAN/control" <<CONTROL
Package: hashcrack
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: JackRipper-ID <JackRipper-ID@users.noreply.github.com>
Installed-Size: 130
Depends: python3 (>= 3.8)
Recommends: python3-bcrypt, python3-passlib, p7zip-full
Homepage: https://github.com/JackRipper-ID/hashcrack
Description: Animated local hash cracker (CPU-only)
 HASHCRACK cracks 39+ hash formats (MD5, SHA family, bcrypt, md5crypt,
 sha512crypt, phpass, PBKDF2 and more) with a fully animated terminal UI.
 Attack modes: wordlist, wordlist+rules, mask, PIN, literal and two-wordlist
 combo. Also cracks encrypted ZIPs. On rooted Android/Termux it auto-boosts
 CPU clocks.
CONTROL

cat > "$DEB/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && \
  update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
  gtk-update-icon-cache -qtf /usr/share/icons/hicolor || true
echo ""
echo "  HASHCRACK installed."
echo "  Terminal : hashcrack"
echo "  App menu : HASHCRACK  (opens a terminal window automatically)"
echo ""
exit 0
POSTINST
chmod 755 "$DEB/DEBIAN/postinst"

fakeroot dpkg-deb --build --root-owner-group "$DEB" "hashcrack_${VERSION}_all.deb"
echo ""
echo "Done:"
ls -lh "HASHCRACK-${VERSION}-x86_64.AppImage" "hashcrack_${VERSION}_all.deb"
