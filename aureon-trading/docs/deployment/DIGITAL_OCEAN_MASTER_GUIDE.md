# Aureon Trading System - Digital Ocean Master Guide 🌊🦈

This guide ensures the Aureon Trading System runs effectively on the Digital Ocean platform. The system uses a specific architecture (Queen Hive Mind + Orca Kill Cycle) that requires a configured environment.

## 1. Droplet Requirements (The Hardware) 🖥️

To run the "Queen Neuron" and "Whale Sonar" effectively without crashing, your Droplet must meet these specs:

| Component | Minimum Requirement | Recommended (Best Performance) | Reason |
| :--- | :--- | :--- | :--- |
| **RAM** | **2 GB** | **4 GB** | Neural networks & large matrix (pandas/numpy) operations. |
| **CPU** | 1 vCPU | 2 vCPUs | "Stargate" math & 7.83Hz harmonic loop timing. |
| **OS** | Ubuntu 22.04 or 24.04 | Ubuntu 24.04 (LTS) | Modern Python 3.10+ support built-in. |
| **Disk** | 25 GB SSD | 50 GB SSD | Storing log files & "Elephant Memory" JSONs. |

> **Cost Estimate:** The 2GB/1CPU Droplet is typically ~$12/month. The 4GB/2CPU is ~$24/month.

---

## 2. Deployment Method A: One-Click Script (Recommended) 🚀

This is the fastest "Tell it what to do" method. It automates the entire provisioning process.

1.  **Create a Droplet** (Select Ubuntu 24.04, 2GB+ RAM).
2.  **SSH into the Droplet**:
    ```bash
    ssh root@<your_droplet_ip>
    ```
3.  **Run the Auto-Setup**:
    *(Copy and paste this single command block)*
    ```bash
    curl -sSL https://raw.githubusercontent.com/RA-CONSULTING/aureon-trading/main/deploy/droplet-setup.sh | bash
    ```

**What this script does:**
- Installs Python 3.12 & Docker.
- Clones the `aureon-trading` repo to `/root/aureon-trading`.
- Creates a dedicated **Virtual Environment** (`venv`).
- Installs all dependencies (`numpy`, `pandas`, `scipy`, etc.).
- Sets up the `orca-kill-cycle` system service to auto-start on boot.

---

## 3. Configuration (The "Keys to the Kingdom") 🗝️

After the script finishes, you **must** configure your API keys.

1.  **Edit the Environment File**:
    ```bash
    nano /root/aureon-trading/.env
    ```
2.  **Paste your keys** (Kraken, Binance, Alpaca, etc.):
    ```ini
    KRAKEN_API_KEY=your_key_here
    KRAKEN_API_SECRET=your_secret_here
    # ... fill in others ...
    ```
3.  **Restart the Service** to apply changes:
    ```bash
    systemctl restart orca-kill-cycle
    ```

---

## 4. Verification (Is it working?) ✅

Check the status of the Queen and Orca:

**Check Service Status:**
```bash
systemctl status orca-kill-cycle
```

**View Live Logs (The "Matrix" View):**
```bash
journalctl -u orca-kill-cycle -f
```
*You should see logs like: `mind - INFO - 👑 Queen Consciousness Matrix: ONLINE`*

---

## 5. Deployment Method B: Digital Ocean App Platform (Container) 🐳

For a fully managed solution with the Command Center UI, use the **App Platform**.

### 🛠️ The "Auto-Pilot" Configuration (app.yaml)

We have created an `app.yaml` file that tells Digital Ocean EXACTLY what resources the Queen needs (RAM, Ports, Build Commands).

1.  **Go to Digital Ocean Dashboard** -> **Apps** -> **Create App**.
2.  **Select Source**: Choose **GitHub** -> `RA-CONSULTING/aureon-trading`.
3.  **Resources**:
    *   **Edit Plan**: Choose **Pro Professional XS** (1GB RAM) minimum. **Pro Professional S** (2GB RAM) is HIGHLY recommended for the Queen's brain.
    *   *Note: Basic plans may crash with "OutOfMemory" errors.*
4.  **Environment Variables**:
    *   Click "Edit" on Environment Variables.
    *   Add your keys (`KRAKEN_API_KEY`, etc.).
5.  **Build Command**: Dockerfile (Auto-detected).
6.  **Run Command**: `/usr/local/bin/supervisord -n -c /app/deploy/supervisord.conf` (Auto-configured by Dockerfile).

### 🚨 Critical Fixes Applied
We have patched the `Dockerfile` and `start_orca.sh` to ensure:
*   The container starts **both** the Dashboard UI (Port 8080) and the Orca Shark (background).
*   The startup script auto-detects the Python environment to prevent "ModuleNotFound" errors.

### 📜 Check Logs in App Platform
*   Go to the "Runtime Logs" tab.
*   You should see:
    ```
    supervisord started
    spawned: 'command-center' with pid ...
    spawned: 'orca-engine' with pid ...
    mind - INFO - 👑 Queen Consciousness Matrix: ONLINE
    ```

---

## Troubleshooting 🔧

- **"ModuleNotFoundError: No module named numpy"**:
  - **Fix:** Ensure you are using the venv path: `/root/aureon-trading/venv/bin/python`. The service file handles this automatically.

- **"Killed" message in logs**:
  - **Cause:** Out of RAM. The Queen used too much memory.
  - **Fix:** Ugrade Droplet to 4GB RAM or add Swap space:
    ```bash
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    ```
