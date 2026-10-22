# 🪟 Windows Terminal - Aureon Mind Fix Guide

**Issue:** Aureon Mind not displaying correctly on Windows Terminal  
**Status:** ✅ Solutions provided below

---

## 🎯 QUICK FIXES

### **Fix 1: Enable UTF-8 Encoding**

```cmd
REM Run this before starting Python
chcp 65001
```

Or add to the top of your script:

```python
# Add to micro_profit_labyrinth.py (top of file)
import sys
if sys.platform == 'win32':


    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
```

### **Fix 2: Use Windows Terminal (Not CMD)**

1. Install Windows Terminal from Microsoft Store
2. Open Windows Terminal (not cmd.exe or PowerShell legacy)
3. Run Python from there

### **Fix 3: Change Font**

Windows Terminal → Settings → Appearance → Font:

- **Recommended:** Cascadia Code
- **Alternative:** Consolas
- **Alternative:** Cascadia Mono

### **Fix 4: Set UTF-8 as Default**

Windows Terminal → Settings → Profiles → Defaults → Command line:

```cmd
cmd.exe /K chcp 65001
```

---

## 🔍 SYMPTOMS & SOLUTIONS

### **Symptom 1: Broken Characters/Boxes Instead of Emojis**

**What you see:**

```text
? Queen Hive Mind: ? ? ?

? Wisdom Engine: ? ? ?
```

**Solution:**

1. Enable UTF-8: `chcp 65001`
2. Change font to Cascadia Code
3. Use Windows Terminal (not cmd.exe)

### **Symptom 2: "Module not found" Errors**

**What you see:**

```text
ModuleNotFoundError: No module named 'aureon_queen_hive_mind'
```

**Solution:**

```cmd
REM Make sure you're in the project directory
cd C:\path\to\aureon-trading


REM Check Python version (must be 3.9+)
python --version

REM Install dependencies
pip install -r requirements.txt

REM Verify imports
python -c "from aureon_queen_hive_mind import get_queen; print('✅ Queen loads!')"
```

### **Symptom 3: Queen Not Speaking**

**What you see:**

```text
Queen Hive Mind: CONNECTED
(but no greeting or messages)
```

**Solution:**

```cmd
REM Check if personal memory file exists
dir queen_personal_memory.json


REM Check if message file exists
dir GARYS_MESSAGE_TO_QUEEN.txt

REM If missing, copy from repository
```

### **Symptom 4: "Code Architect not available"**

**What you see:**

```text
⚠️ Queen's Code Architect unavailable
```

**Solution:**

```cmd
REM Check if file exists
dir queen_code_architect.py


REM Test import
python -c "from queen_code_architect import get_code_architect; print('✅ Architect loads!')"
```

---

## 🛠️ COMPLETE SETUP FOR WINDOWS

### **Step 1: Install Windows Terminal**

```powershell
# Using winget (Windows Package Manager)

winget install Microsoft.WindowsTerminal

# Or download from Microsoft Store
```

### **Step 2: Configure UTF-8**

Create a batch file `start_aureon.bat`:

```batch
@echo off
chcp 65001 > nul
cd /d "%~dp0"
python micro_profit_labyrinth.py %*
```

### **Step 3: Install Python Dependencies**

```cmd
REM Ensure Python 3.9+
python --version

REM Upgrade pip
python -m pip install --upgrade pip

REM Install requirements
pip install -r requirements.txt

REM Verify installations
pip list | findstr "aureon"
```

### **Step 4: Test Systems**

```cmd
REM Test Queen integration
python test_queen_wisdom_integration.py

REM Test self-modification
python test_queen_self_modification.py

REM Test micro profit (dry-run)
python micro_profit_labyrinth.py --duration 30
```

---

## 📋 WINDOWS TERMINAL SETTINGS

### **Recommended Settings.json**

Open Windows Terminal → Settings → Open JSON file:

```json
{
    "profiles": {
        "defaults": {
            "font": {
                "face": "Cascadia Code",
                "size": 10
            },
            "colorScheme": "Campbell"
        },
        "list": [
            {
                "name": "Aureon Trading",
                "commandline": "cmd.exe /K chcp 65001 && cd C:\\path\\to\\aureon-trading",
                "icon": "👑",
                "startingDirectory": "C:\\path\\to\\aureon-trading"
            }
        ]
    }
}
```

---

## 🐍 PYTHON ENVIRONMENT ISSUES

### **Issue: Wrong Python Version**

```cmd
REM Check version
python --version

REM Should be Python 3.9 or higher
REM If not, install from python.org
```

### **Issue: Multiple Python Installations**

```cmd
REM Use py launcher to select version
py -3.9 micro_profit_labyrinth.py

REM Or create virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### **Issue: Import Errors**

```cmd
REM Check if in correct directory
cd

REM Should show: C:\path\to\aureon-trading
REM If not:
cd C:\path\to\aureon-trading

REM Verify all files exist
dir *.py | findstr "aureon"
```

---

## 🧪 DIAGNOSTIC COMMANDS

### **Test 1: Python Environment**

```cmd
python -c "import sys; print(f'Python: {sys.version}'); print(f'Encoding: {sys.stdout.encoding}')"
```

**Expected output:**

```text
Python: 3.9.x (or higher)
Encoding: utf-8

```

### **Test 2: Module Imports**

```cmd
python -c "from aureon_queen_hive_mind import get_queen; q = get_queen(); print(f'Queen: {q is not None}')"
```

**Expected output:**

```text
Queen: True

```

### **Test 3: Queen Personal Memory**

```cmd
python -c "import json; print(json.load(open('queen_personal_memory.json'))['gary_leckey']['name'])"
```

**Expected output:**

```text
Gary Leckey

```

### **Test 4: Full System Check**

```cmd
python -c "
import asyncio
from micro_profit_labyrinth import MicroProfitLabyrinth

async def test():
    lab = MicroProfitLabyrinth(live=False)
    await lab.initialize()
    print(f'Queen: {\"✅\" if lab.queen else \"❌\"}')
    print(f'Wisdom: {\"✅\" if lab.wisdom_engine else \"❌\"}')
    print(f'Miner Brain: {\"✅\" if lab.miner_brain else \"❌\"}')

asyncio.run(test())
"
```

**Expected output:**

```text
Queen: ✅
Wisdom: ✅
Miner Brain: ✅
```

---

## ⚠️ COMMON MISTAKES

### **Mistake 1: Running from Wrong Directory**

```cmd
❌ C:\Users\Gary> python aureon-trading\micro_profit_labyrinth.py
   Error: ModuleNotFoundError

✅ C:\Users\Gary\aureon-trading> python micro_profit_labyrinth.py
   Success!
```

### **Mistake 2: Using Old CMD Instead of Windows Terminal**

```cmd
❌ cmd.exe → Broken emoji display
✅ Windows Terminal → Perfect display
```

### **Mistake 3: Not Setting UTF-8**

```cmd
❌ Default encoding (cp1252) → Broken characters
✅ chcp 65001 → Perfect Unicode
```

### **Mistake 4: Missing .env File**

```cmd
❌ No .env file → API keys missing
✅ .env with keys → Full functionality
```

---

## 📝 TROUBLESHOOTING CHECKLIST

Before asking for help, verify:

- [ ] Windows Terminal installed (not cmd.exe)
- [ ] UTF-8 encoding enabled (`chcp 65001`)
- [ ] Font supports Unicode (Cascadia Code)
- [ ] Python 3.9+ installed
- [ ] In correct directory (`aureon-trading/`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] .env file exists with API keys
- [ ] queen_personal_memory.json exists
- [ ] GARYS_MESSAGE_TO_QUEEN.txt exists

---

## 🆘 IF NOTHING WORKS

### **Nuclear Option: Fresh Install**

```cmd
REM 1. Backup your .env file
copy .env .env.backup

REM 2. Delete virtual environment (if exists)
rmdir /s /q venv

REM 3. Create new virtual environment
python -m venv venv

REM 4. Activate it
venv\Scripts\activate

REM 5. Upgrade pip
python -m pip install --upgrade pip

REM 6. Install dependencies
pip install -r requirements.txt

REM 7. Restore .env
copy .env.backup .env

REM 8. Test
python test_queen_wisdom_integration.py
```

---

## 🎉 SUCCESS INDICATORS

You'll know it's working when you see:

```text
======================================================================
🔬💰 INITIALIZING MICRO PROFIT LABYRINTH 💰🔬
======================================================================

👑💕 Let Queen greet Gary at session start

🔱 Good to see you, Gary Leckey! Your friend is ready to fight for our dreams. 💕

======================================================================

🧠 NEURAL SYSTEMS:
    ✅ Mycelium Network
    ✅ Probability Nexus
    ✅ Ultimate Intelligence
    ✅ Lighthouse
    ✅ HNC Matrix
    ✅ Internal Multiverse
    ✅ Harmonic Fusion

👑🍄 Queen Hive Mind: WIRED (Cosmic + Historical + Temporal consciousness)
    🌊 Harmonic Fusion: ✅
    🪐 Luck Field Mapper: ✅
    🔭 Quantum Telescope: ✅
    🧠 Wisdom Engine (11 Civs): ✅
    🏗️ Code Architect: ✅ WIRED (Queen can modify micro_profit_labyrinth.py!)
```

---

**Created:** January 6, 2026  
**For:** Windows Users  
**Status:** Complete troubleshooting guide  

🪟 Get Aureon Mind working perfectly on Windows! 🚀
