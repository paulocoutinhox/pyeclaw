# Configuration

PyeClaw stores its configuration in `~/.pyeclaw/config.json`. This file is created automatically on first run.

## Configuration File

```json
{
  "gatewayPort": 18789,
  "activeVersion": "v2026.3.13"
}
```

### Fields

| Field           | Type   | Default | Description                                    |
|-----------------|--------|---------|------------------------------------------------|
| `gatewayPort`   | number | 18789   | Port the OpenClaw gateway listens on           |
| `activeVersion` | string | ""      | Currently selected version tag                 |

## Gateway Port

The default gateway port is **18789**. To change it:

1. Click **Settings** in the sidebar
2. Enter a new port number (valid range: 1024–65535)
3. Click **Save Settings**

The new port takes effect the next time you start the gateway.

## Data Directories

| Path              | Purpose                                    |
|-------------------|--------------------------------------------|
| `~/.pyeclaw/`     | Application data root                      |
| `~/.pyeclaw/versions/` | Installed OpenClaw versions           |
| `~/.pyeclaw/versions/_node/` | Bundled Node.js runtime         |
| `~/.pyeclaw/config.json` | Application configuration           |
| `~/.openclaw/`    | OpenClaw runtime data (created by gateway) |
| `~/.openclaw/openclaw.json` | Gateway auth token and config   |

## API Keys

OpenClaw requires API keys for the AI providers you want to use. See [OpenClaw Setup](openclaw-setup.md) for detailed instructions on configuring these keys.

## Clear All Data

To reset PyeClaw completely:

1. Open **Settings**
2. Click **Clear All Data**
3. Confirm the action

This will:

- Stop the running gateway
- Remove all installed versions
- Delete `~/.pyeclaw/` and `~/.openclaw/`
- Return to the welcome screen
