# 🚀 AUREON TRADING SYSTEM - WINDOWS LOCAL SETUP GUIDE

**Quick Start for Windows 10/11 with Python 3.9+**

---

## 📋 Prerequisites

✅ **Python 3.9+** - Download from https://www.python.org/downloads/
✅ **Node.js 18+ (LTS)** - Download from https://nodejs.org/en/download/ (includes npm)
✅ **Git** - https://git-scm.com/download/win
✅ **Visual C++ Build Tools** (for some dependencies)

---

## 🔧 Step 1: Clone the Repository

```powershell
# Open PowerShell or CMD
cd C:\Users\YourName\Projects

# Clone the repository
git clone https://github.com/RA-CONSULTING/aureon-trading.git
cd aureon-trading
```

---

## 🐍 Step 2: Create Python Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate it (PowerShell)
.\.venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate again:
.\.venv\Scripts\Activate.ps1

# Or in CMD:
.venv\Scripts\activate.bat
```

---

## 📦 Step 3: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# If requirements.txt issues, install core packages:
pip install numpy pandas requests asyncio websockets aiohttp python-dotenv
```

---

## ⚙️ Step 4: Configure Environment

```powershell
# Copy example .env
Copy-Item .env.example .env

# Edit .env with your API keys
# ✅ Add: KRAKEN_API_KEY, KRAKEN_API_SECRET
# ✅ Add: BINANCE_API_KEY, BINANCE_API_SECRET  
# ✅ Add: ALPACA_API_KEY, ALPACA_API_SECRET
```

Edit `.env` in a text editor (VS Code recommended):
```
KRAKEN_API_KEY=your_key_here
KRAKEN_API_SECRET=your_secret_here
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
```

---

## 🧪 Step 5: Test Basic Functionality

```powershell
# Test imports
python -c "import aureon_chirp_bus; print('✅ Chirp Bus OK')"
python -c "import aureon_thought_bus; print('✅ Thought Bus OK')"
python -c "import aureon_queen_hive_mind; print('✅ Queen OK')"

# If all show ✅, you're ready!
```

---

## 🎯 Step 6: Run Simple Test

```powershell
# Quick smoke test
python -c "
from aureon_probability_nexus import AureonProbabilityNexus
nexus = AureonProbabilityNexus()
print('🔮 Probability Nexus initialized successfully')
print('✅ System ready for trading')
"
```

---

## 🖥️ Step 7: Start the Dashboard (Frontend)

```powershell
# Navigate to the frontend folder
cd frontend

# Install frontend dependencies (first time only)
npm install

# Start the dashboard
npm run dev
```

Then open **http://localhost:3000** (or the URL shown in the terminal) in your browser.

> **Note:** If `npm` is not recognised, install Node.js from https://nodejs.org/en/download/, then close and reopen PowerShell.

---

## 🚀 Step 8: Start Trading (Dry-Run First!)

```powershell
# Test mode - no real trades
python micro_profit_labyrinth.py --dry-run

# Or start the ecosystem
python run_unified_ecosystem.py

# Check the logs
type trading.log

# Or watch live (PowerShell)
Get-Content -Path trading.log -Wait
```

---

## 🔥 Windows-Specific Fixes

### Issue: "UTF-8 encoding error on Windows"
✅ **FIXED** - All files have Windows UTF-8 wrapper at top

### Issue: "asyncio event loop error"
✅ **FIXED** - Use `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`

### Issue: "WebSocket connection timeout"
✅ Try increasing timeout in `alpaca_sse_client.py`:
```python
timeout = aiohttp.ClientTimeout(total=30)  # Increase from 10s
```

### Issue: "Permission denied on queen_configs/"
```powershell
# Clean up old learning states
Remove-Item -Path queen_configs\learning_state_turn_*.json -Force
```

---

## 📊 File Structure (Windows)

```
C:\Users\YourName\Projects\aureon-trading\
├── .venv\                        # Your Python environment
├── .env                          # Your API keys (DON'T COMMIT!)
├── aureon_chirp_bus.py          # ✅ Singing at kHz speeds
├── aureon_queen_hive_mind.py    # 👑 Queen decision engine
├── micro_profit_labyrinth.py    # 💰 Execution engine
├── aureon_orca_intelligence.py  # 🦈 Whale hunter
├── aureon_probability_nexus.py  # 🔮 Validation (Batten Matrix)
├── requirements.txt
└── trading.log                  # Live trading logs
```

---

## 🎵 Chirp Bus on Windows

✅ **Fully Windows-compatible!**

Chirps emit at kHz speeds using shared memory:
- **No special Windows setup needed**
- Automatic fallback to ThoughtBus if shared memory unavailable
- All 9 systems singing: Queen → Orca → Micro → HFT → Nexus → Enigma → Elephant → Ecosystem → Scanner

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'aureon_...'"
```powershell
# Make sure you're in the right directory and venv is activated
cd C:\Users\YourName\Projects\aureon-trading
.\.venv\Scripts\Activate.ps1
```

### "API connection refused"
```powershell
# Check your internet connection
ping github.com

# Verify API keys in .env
Get-Content .env | Select-String "API_KEY"

# Test exchange connectivity
python check_all_balances.py
```

### "Cannot open file: The system cannot find the file specified"
```powershell
# Make sure you're in the right folder
Get-Location  # Should show aureon-trading

# List files to verify
Get-ChildItem -Filter "*.py" | Select-Object Name | head -10
```

---

## 📈 Next Steps

1. **Verify Balances**: `python check_all_balances.py`
2. **Dry-Run Test**: `python micro_profit_labyrinth.py --dry-run`
3. **Enable Logging**: Check `trading.log` for activity
4. **Start Hunting**: `python aureon_orca_intelligence.py`
5. **Monitor Queen**: Watch Queen Hive Mind decisions

---

## 🚨 IMPORTANT - SAFETY FIRST

Before live trading:
- ✅ Test on dry-run mode first (at least 1 hour)
- ✅ Start with minimal position sizes ($1-5)
- ✅ Monitor your API rate limits
- ✅ Keep backup of `.env` file (but DON'T commit it!)
- ✅ Enable 2FA on your exchange accounts

---

## 💻 Command Cheat Sheet (Windows PowerShell)

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Check Python version
python --version

# Install new package
pip install package_name

# Run trading system
python micro_profit_labyrinth.py --dry-run

# View logs (live)
Get-Content -Path trading.log -Wait

# Stop running process
Ctrl + C

# Deactivate environment
deactivate
```

---

## 🎯 You're Ready!

Your Windows machine is now configured to run the Aureon Trading System with:
- ✅ **Chirp Bus** (kHz-speed communication - 2.3× faster)
- ✅ **Queen Hive Mind** (Supreme decision controller)
- ✅ **Orca Intelligence** (Whale hunter mode)
- ✅ **Micro Profit** (Execution engine)
- ✅ **Full Windows UTF-8 support**

**Let's make some profit!** 🚀

---

*Gary Leckey | January 2026*  
*"Windows ready. Queen online. Systems singing. Let's hunt whales."* 🦈⚡
