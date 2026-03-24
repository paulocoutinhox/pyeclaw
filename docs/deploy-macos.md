# Deploy — macOS

## Prerequisites

- Python 3.11+
- pip
- PyInstaller
- Xcode command line tools (for signing)

## Building Locally

### Install Dependencies

```bash
pip install -e .
pip install pyinstaller
```

### Build the Application

```bash
pyinstaller \
  --name PyeClaw \
  --windowed \
  --onedir \
  --icon pyeclaw/resources/icon.icns \
  --add-data "pyeclaw/resources:pyeclaw/resources" \
  --add-data "extras/images:extras/images" \
  pyeclaw/app.py
```

The built application will be at `dist/PyeClaw.app`.

### Create a .pkg Installer

```bash
productbuild \
  --component dist/PyeClaw.app /Applications \
  --sign "Developer ID Installer: Your Name (TEAM_ID)" \
  dist/PyeClaw.pkg
```

## Code Signing

### Requirements

- Apple Developer account
- Developer ID Application certificate
- Developer ID Installer certificate

### Sign the App

```bash
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  --entitlements entitlements.plist \
  dist/PyeClaw.app
```

### Notarize

```bash
xcrun notarytool submit dist/PyeClaw.pkg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

xcrun stapler staple dist/PyeClaw.pkg
```

## Mac App Store

### Certificates

You need two certificates from your Apple Developer account:

1. **Mac App Distribution** — signs the app
2. **Mac Installer Distribution** — signs the .pkg

### App ID

Create an App ID in the Apple Developer portal:

- Bundle ID: `com.pyeclaw.app`
- Capabilities: Network (Client)

### Build for MAS

```bash
pyinstaller \
  --name PyeClaw \
  --windowed \
  --onedir \
  --icon pyeclaw/resources/icon.icns \
  --add-data "pyeclaw/resources:pyeclaw/resources" \
  --add-data "extras/images:extras/images" \
  --osx-bundle-identifier com.pyeclaw.app \
  pyeclaw/app.py
```

### Submit

```bash
xcrun altool --upload-app \
  --type macos \
  --file dist/PyeClaw.pkg \
  --apiKey "API_KEY" \
  --apiIssuer "API_ISSUER"
```

## CI/CD (GitHub Actions)

### Required Secrets

| Secret                 | Description                              |
|------------------------|------------------------------------------|
| `APPLE_CERTIFICATE`    | Base64-encoded .p12 certificate          |
| `APPLE_CERTIFICATE_PWD`| Certificate password                     |
| `APPLE_ID`             | Apple ID email                           |
| `APPLE_TEAM_ID`        | Developer Team ID                        |
| `APPLE_APP_PWD`        | App-specific password for notarization   |

### Workflow

See `.github/workflows/release.yml` for the automated build and release workflow.
