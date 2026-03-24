# Deploy — Linux

## Prerequisites

- Python 3.11+
- pip
- PyInstaller

## Building Locally

### Install Dependencies

```bash
pip install -e .
pip install pyinstaller
```

### System Dependencies

```bash
sudo apt-get install -y libgl1-mesa-dev libxkbcommon-x11-0
```

### Build the Application

```bash
pyinstaller \
  --name PyeClaw \
  --windowed \
  --onedir \
  --add-data "pyeclaw/resources:pyeclaw/resources" \
  --add-data "extras/images:extras/images" \
  pyeclaw/app.py
```

The built application will be at `dist/PyeClaw/`.

## Creating a .deb Package

### Directory Structure

```bash
mkdir -p pyeclaw-deb/DEBIAN
mkdir -p pyeclaw-deb/usr/local/bin
mkdir -p pyeclaw-deb/usr/share/applications
mkdir -p pyeclaw-deb/usr/share/icons/hicolor/256x256/apps
mkdir -p pyeclaw-deb/opt/pyeclaw
```

### Control File

Create `pyeclaw-deb/DEBIAN/control`:

```
Package: pyeclaw
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Paulo Coutinho
Description: Desktop manager for OpenClaw
 Install, update, and manage OpenClaw versions with a graphical interface.
```

### Install Files

```bash
cp -r dist/PyeClaw/* pyeclaw-deb/opt/pyeclaw/
cp extras/images/icon.png pyeclaw-deb/usr/share/icons/hicolor/256x256/apps/pyeclaw.png
ln -sf /opt/pyeclaw/PyeClaw pyeclaw-deb/usr/local/bin/pyeclaw
```

### Desktop Entry

Create `pyeclaw-deb/usr/share/applications/pyeclaw.desktop`:

```ini
[Desktop Entry]
Name=PyeClaw
Comment=Desktop manager for OpenClaw
Exec=/opt/pyeclaw/PyeClaw
Icon=pyeclaw
Type=Application
Categories=Development;Utility;
```

### Build .deb

```bash
dpkg-deb --build pyeclaw-deb dist/pyeclaw_1.0.0_amd64.deb
```

## AppImage

Use [appimage-builder](https://appimage-builder.readthedocs.io/) to create a portable AppImage.

## CI/CD (GitHub Actions)

### Required Dependencies

```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y libgl1-mesa-dev libxkbcommon-x11-0
```

### Workflow

See `.github/workflows/release.yml` for the automated build and release workflow.
