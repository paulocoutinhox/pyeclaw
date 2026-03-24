# Getting Started

This guide walks you through installing and running PyeClaw for the first time.

## Installation

### From Release

1. Go to the [Releases](https://github.com/paulocoutinhox/pyeclaw/releases/latest) page
2. Download the installer for your operating system:
   - **macOS**: `.pkg` file
   - **Windows**: `.exe` installer
   - **Linux**: `.deb` package
3. Run the installer and follow the prompts

### From Source

Requirements:

- Python 3.11 or later
- pip (included with Python)

```bash
git clone https://github.com/paulocoutinhox/pyeclaw.git
cd pyeclaw
pip install -e .
python -m pyeclaw
```

## First Run

When you open PyeClaw for the first time:

1. The app detects available OpenClaw versions from GitHub
2. Click **Install Latest** to download and build the most recent version
3. Wait for the installation to complete (this may take a few minutes)
4. The app automatically switches to the main dashboard

## Using the Dashboard

### Sidebar

- **System Info**: Shows your hostname, local IP, and gateway port
- **Versions**: Lists all installed OpenClaw versions
- **Settings**: Opens the settings panel

### Terminal

The built-in terminal provides a shell session inside the selected OpenClaw version directory. The `openclaw` command is available in the terminal PATH.

### Starting the Gateway

1. Hover over a version in the sidebar
2. Click the **play** button to start the gateway
3. The status indicator turns green when the gateway is running
4. Click **Open Control Panel** to access OpenClaw in your browser

### Switching Versions

Click on a different version in the sidebar to switch the terminal context. If the gateway is running with a different version, you will be prompted to confirm.

### Logs

Click the **Logs** tab to view real-time gateway output. Each version maintains its own log buffer.

## Next Steps

- [Configuration](configuration.md) — Configure the gateway port and API keys
- [OpenClaw Setup](openclaw-setup.md) — Set up OpenAI and Anthropic API keys
