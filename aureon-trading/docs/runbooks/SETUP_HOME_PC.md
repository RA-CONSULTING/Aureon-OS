# 🏠 Run Aureon Trading 24/7 on Home PC

## Quick Setup (5 minutes)

### 1️⃣ Install Python 3.10+
- **Windows:** https://python.org/downloads
- **Mac:** `brew install python`
- **Linux:** `sudo apt install python3 python3-pip`

### 2️⃣ Clone the repo
```bash
git clone https://github.com/RA-CONSULTING/aureon-trading
cd aureon-trading
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Copy your .env file
Copy your `.env` file from Codespaces to this folder (contains your API keys)

### 5️⃣ Run 24/7

**Linux/Mac (recommended):**
```bash
# Install tmux
sudo apt install tmux  # Linux
brew install tmux      # Mac

# Start trading in tmux
tmux new -s trading
source .env && LIVE=1 python3 aureon_unified_ecosystem.py

# Detach: Ctrl+B then D
# Reattach: tmux attach -t trading
```

**Windows:**
```powershell
# Run in PowerShell
$env:LIVE="1"
python aureon_unified_ecosystem.py

# Or create a batch file: start_trading.bat
# Contents:
# set LIVE=1
# python aureon_unified_ecosystem.py
```

---

## 🔥 Auto-Start on Boot

### Linux (systemd)
```bash
sudo nano /etc/systemd/system/aureon.service
```
Paste:
```ini
[Unit]
Description=Aureon Trading Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/aureon-trading
EnvironmentFile=/home/YOUR_USERNAME/aureon-trading/.env
ExecStart=/usr/bin/python3 aureon_unified_ecosystem.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Then:
```bash
sudo systemctl enable aureon
sudo systemctl start aureon
sudo systemctl status aureon  # Check status
journalctl -u aureon -f       # View logs
```

### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task → "Aureon Trading"
3. Trigger: "When computer starts"
4. Action: Start a program
   - Program: `python`
   - Arguments: `aureon_unified_ecosystem.py`
   - Start in: `C:\path\to\aureon-trading`
5. Check "Run with highest privileges"

### Mac (launchd)
```bash
nano ~/Library/LaunchAgents/com.aureon.trading.plist
```
Paste:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aureon.trading</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/YOUR_USERNAME/aureon-trading/aureon_unified_ecosystem.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/aureon-trading</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>LIVE</key>
        <string>1</string>
    </dict>
</dict>
</plist>
```
Then: `launchctl load ~/Library/LaunchAgents/com.aureon.trading.plist`

---

## 📊 Monitor Remotely

View logs from anywhere:
```bash
# SSH into your PC
ssh user@your-home-ip

# Check trading
tmux attach -t trading
# or
journalctl -u aureon -f
```

---

## 🔥 8/8 Systems Active - GET THAT MONEY! 🚀

