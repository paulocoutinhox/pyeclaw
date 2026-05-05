# Deploy — Windows

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

### Build the Application

```bash
pyinstaller ^
  --name PyeClaw ^
  --windowed ^
  --onedir ^
  --icon pyeclaw\resources\icon.ico ^
  --add-data "pyeclaw\resources;pyeclaw\resources" ^
  --add-data "extras\images;extras\images" ^
  pyeclaw\app.py
```

The built application will be at `dist\PyeClaw\`.

### Create an Installer

Use [NSIS](https://nsis.sourceforge.io/) or [Inno Setup](https://jrsoftware.org/isinfo.php) to create an `.exe` installer from the `dist\PyeClaw\` directory.

#### Inno Setup Example

```iss
[Setup]
AppName=PyeClaw
AppVersion=1.0.0
DefaultDirName={autopf}\PyeClaw
DefaultGroupName=PyeClaw
OutputBaseFilename=PyeClaw-Setup
SetupIconFile=pyeclaw\resources\icon.ico

[Files]
Source: "dist\PyeClaw\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\PyeClaw"; Filename: "{app}\PyeClaw.exe"
Name: "{autodesktop}\PyeClaw"; Filename: "{app}\PyeClaw.exe"
```

## Code Signing

### Using signtool

```bash
signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 dist\PyeClaw\PyeClaw.exe
```

## CI/CD (GitHub Actions)

### Required Secrets

| Secret              | Description                          |
|---------------------|--------------------------------------|
| `WINDOWS_CERT`      | Base64-encoded .pfx certificate      |
| `WINDOWS_CERT_PWD`  | Certificate password                 |

### Workflow

See `.github/workflows/release.yml` for the automated build and release workflow.
