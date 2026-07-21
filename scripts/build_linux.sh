#!/usr/bin/env bash
# ============================================================================
# Linux Build Script for Media Downloader
# ============================================================================
# Builds a standalone Linux binary with PyInstaller.
#
# Usage:
#   ./scripts/build_linux.sh              # Build binary only
#   ./scripts/build_linux.sh installer     # Build binary + AppImage/.deb
#   ./scripts/build_linux.sh full          # Download deps + build binary
#   ./scripts/build_linux.sh full installer # Everything
#
# Environment:
#   BUNDLE_CHROMIUM=1  Bundle Chromium (~150 MB extra)
#   BUNDLE_CHROMIUM=0  Download on first launch (default)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SPEC_FILE="$PROJECT_ROOT/media_downloader_linux.spec"
DIST_DIR="$PROJECT_ROOT/dist"
INSTALLERS_DIR="$PROJECT_ROOT/installers"
BUILD_MODE="${1:-binary}"

BUNDLE_CHROMIUM="${BUNDLE_CHROMIUM:-0}"
APP_NAME="MediaDownloader"
VERSION="1.2.0"

echo "========================================================"
echo " Media Downloader Linux Build"
echo "========================================================"
echo "Mode:            $BUILD_MODE"
echo "Bundle Chromium: $BUNDLE_CHROMIUM"
echo "Version:         $VERSION"
echo "========================================================"
echo ""

# ------------------------------------------------------------------
# Download external dependencies
# ------------------------------------------------------------------
if [ "$BUILD_MODE" = "full" ] || [ "$BUILD_MODE" = "full installer" ]; then
    echo ">>> Downloading ffmpeg..."
    python3 "$SCRIPT_DIR/download_ffmpeg_linux.py" || echo "WARNING: ffmpeg download failed"

    if [ "$BUNDLE_CHROMIUM" = "1" ]; then
        echo ">>> Downloading Chromium..."
        python3 "$SCRIPT_DIR/download_chromium.py" || echo "WARNING: Chromium download failed"
    fi
fi

# ------------------------------------------------------------------
# Clean previous build artifacts
# ------------------------------------------------------------------
echo ">>> Cleaning previous build..."
rm -rf "$DIST_DIR/$APP_NAME" "$PROJECT_ROOT/build"

# ------------------------------------------------------------------
# Run PyInstaller (via uv to pick up project venv)
# ------------------------------------------------------------------
echo ">>> Running PyInstaller..."
cd "$PROJECT_ROOT"
PYINSTALLER_CMD="pyinstaller"
if command -v uv &>/dev/null && [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER_CMD="uv run pyinstaller"
fi
BUNDLE_CHROMIUM="$BUNDLE_CHROMIUM" $PYINSTALLER_CMD "$SPEC_FILE" --noconfirm

# ------------------------------------------------------------------
# Verify binary
# ------------------------------------------------------------------
BINARY="$DIST_DIR/$APP_NAME/MediaDownloader"
if [ -f "$BINARY" ]; then
    echo "✓ Binary found at: $BINARY"
    file "$BINARY"
else
    echo "✗ ERROR: Binary not found at $BINARY"
    exit 1
fi

echo ""
echo "========================================================"
echo " Build Complete"
echo "========================================================"
echo ""
echo "Portable binary: $DIST_DIR/$APP_NAME/"
echo ""

# ------------------------------------------------------------------
# Create .deb package (installer mode)
# ------------------------------------------------------------------
if [ "$BUILD_MODE" = "installer" ] || [ "$BUILD_MODE" = "full installer" ]; then
    echo ">>> Creating .deb package..."
    mkdir -p "$INSTALLERS_DIR"

    DEB_DIR="/tmp/media-downloader-deb"
    rm -rf "$DEB_DIR"
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/opt/MediaDownloader"
    mkdir -p "$DEB_DIR/usr/bin"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"

    # Copy all build artifacts
    cp -r "$DIST_DIR/$APP_NAME/"* "$DEB_DIR/opt/MediaDownloader/"
    chmod +x "$DEB_DIR/opt/MediaDownloader/MediaDownloader"

    # Symlink in PATH
    ln -sf /opt/MediaDownloader/MediaDownloader "$DEB_DIR/usr/bin/media-downloader"

    # Desktop entry
    cat > "$DEB_DIR/usr/share/applications/media-downloader.desktop" << DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Media Downloader
Comment=Download media from YouTube, Spotify, SoundCloud, TikTok, and more
Exec=/opt/MediaDownloader/MediaDownloader
Icon=media-downloader
Categories=AudioVideo;Network;
Terminal=false
DESKTOP_EOF

    # Icon (use .ico as fallback, convert to .png if ImageMagick is available)
    if command -v convert &>/dev/null; then
        convert "$PROJECT_ROOT/assets/media_downloader.ico" \
            "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/media-downloader.png"
    else
        # Minimal 1x1 transparent PNG as placeholder
        echo "WARNING: ImageMagick not installed — icon won't be in .deb"
    fi

    # Build control file
    cat > "$DEB_DIR/DEBIAN/control" << CONTROL_EOF
Package: media-downloader
Version: $VERSION
Section: net
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.10), libxcb-xkb1, libxkbcommon0
Recommends: ffmpeg
Maintainer: Media Downloader Team
Description: Download media from YouTube, Spotify, SoundCloud, TikTok,
 Instagram, Twitter, Pinterest, RadioJavan, and more.
 .
 A cross-platform GUI application built with Python and CustomTkinter.
CONTROL_EOF

    # Post-install: ensure ffmpeg is available
    cat > "$DEB_DIR/DEBIAN/postinst" << 'POSTINST_EOF'
#!/bin/sh
set -e
echo "Media Downloader installed."
echo "For audio downloads, install ffmpeg: sudo apt install ffmpeg"
POSTINST_EOF
    chmod +x "$DEB_DIR/DEBIAN/postinst"

    # Build .deb
    DEB_OUTPUT="$INSTALLERS_DIR/media-downloader_${VERSION}_amd64.deb"
    dpkg-deb --build "$DEB_DIR" "$DEB_OUTPUT"

    echo ""
    echo "✓ .deb package: $DEB_OUTPUT"
    echo ""
fi
