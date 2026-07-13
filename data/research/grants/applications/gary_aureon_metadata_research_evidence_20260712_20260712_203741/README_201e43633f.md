# AUREON Desktop Launcher (Component)

Scope: This is an optional Windows launcher for the unified trading engine. For the system overview, setup, and run instructions, see the root [README.md](../README.md) and [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

Windows desktop application for running AUREON Quantum Trading System.

## Features

- **Setup Wizard** - First-time API key configuration
- **Windows Credential Manager** - Secure key storage (never in files)
- **One-Click Start/Stop** - Simple trading controls
- **Activity Log** - Real-time trading activity display
- **Web Dashboard Link** - Quick access to full monitoring

## Quick Start

### Option 1: Run from Source

```powershell
# Install dependencies
pip install -r requirements.txt

# Run the launcher
python launcher.py
```

### Option 2: Build Standalone .exe

```powershell
# Run the build script
.\build.bat

# The executable will be in dist\aureon.exe
```

## First-Time Setup

1. Launch the application
2. Follow the Setup Wizard to enter your exchange API keys
3. Keys are stored securely in Windows Credential Manager
4. Click "START TRADING" to begin

## Supported Exchanges

- 🟡 **Binance** - Crypto trading (recommended)
- 🐙 **Kraken** - Crypto trading
- 🦙 **Alpaca** - US stocks
- 💼 **Capital.com** - CFDs

## Security Notes

⚠️ **IMPORTANT**:
- Only enable **SPOT trading** permissions on your API keys
- **NEVER** enable withdrawal permissions
- Keys are stored in Windows Credential Manager, not in files
- The app never transmits your keys anywhere except to the exchanges

## File Structure

```
aureon_launcher/
├── launcher.py        # Main application
├── credentials.py     # Windows Credential Manager integration
├── setup_wizard.py    # First-time setup wizard
├── requirements.txt   # Python dependencies
├── build.bat          # Build script for .exe
└── README.md          # This file
```

## Requirements

- Windows 10/11
- Python 3.10+ (for source) or none (for .exe)
- Exchange API keys

## Troubleshooting

**"Trading script not found"**
- Make sure `aureon_kraken_ecosystem.py` is in the parent directory

**"Failed to save credentials"**
- Run as Administrator if Windows Credential Manager access is blocked

**API key errors**
- Verify your API keys are correct and have SPOT trading enabled
- Check that IP restrictions (if any) include your current IP

## Web Dashboard

The full monitoring dashboard is available at:
https://owfeyxrfyhprpcgqwxqh.lovableproject.com/

Click "Open Dashboard" in the launcher to access it.
