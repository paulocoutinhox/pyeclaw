# OpenClaw Setup

After installing an OpenClaw version through PyeClaw, you need to configure API keys for the AI providers you want to use.

## Supported Providers

OpenClaw supports the following AI providers:

- **OpenAI** (GPT-4, GPT-4o, etc.)
- **Anthropic** (Claude)

You need at least one provider configured to use OpenClaw.

## Getting API Keys

### OpenAI

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to **API Keys** in the left sidebar
4. Click **Create new secret key**
5. Give it a name (e.g., "OpenClaw") and click **Create**
6. Copy the key — it starts with `sk-`

### Anthropic

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to **API Keys** in the sidebar
4. Click **Create Key**
5. Give it a name (e.g., "OpenClaw") and click **Create Key**
6. Copy the key — it starts with `sk-ant-`

## Setting Environment Variables

Set the API keys as environment variables so OpenClaw can access them.

### macOS

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export OPENAI_API_KEY="sk-your-openai-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"
```

Then reload your shell:

```bash
source ~/.zshrc
```

### Windows

#### Using PowerShell (persistent)

```powershell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-openai-key-here", "User")
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-your-anthropic-key-here", "User")
```

#### Using System Settings

1. Open **Settings** → **System** → **About** → **Advanced system settings**
2. Click **Environment Variables**
3. Under **User variables**, click **New**
4. Add `OPENAI_API_KEY` with your OpenAI key
5. Add `ANTHROPIC_API_KEY` with your Anthropic key
6. Click **OK** and restart PyeClaw

### Linux

Add to your shell profile (`~/.bashrc` or `~/.profile`):

```bash
export OPENAI_API_KEY="sk-your-openai-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-anthropic-key-here"
```

Then reload:

```bash
source ~/.bashrc
```

## Verifying the Setup

1. Open PyeClaw
2. Start the gateway by clicking the play button on a version
3. Open the built-in terminal
4. Run:

```bash
openclaw --version
```

If the gateway starts successfully and you can access the control panel, your API keys are configured correctly.

## Troubleshooting

### Gateway fails to start

- Check that your API keys are set in the environment
- Restart PyeClaw after setting environment variables
- Check the **Logs** tab for error messages

### "API key not found" errors

- Make sure the environment variable names are exactly `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`
- On macOS/Linux, ensure you added the exports to the correct shell profile
- On Windows, restart PyeClaw after setting system environment variables

### Port already in use

- Change the gateway port in **Settings**
- Or stop any other service using port 18789
