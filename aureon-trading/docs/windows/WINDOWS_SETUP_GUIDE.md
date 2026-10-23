# 🪟 Windows Setup Guide for Aureon Trading

It looks like you are setting up the system on a fresh Windows machine. Follow these steps exactly to get everything running.

## Step 1: Install Node.js
The frontend dashboard requires Node.js (which includes `npm`).

1.  Open your browser and go to **https://nodejs.org/en/download/**
2.  Click the **LTS** download button (recommended for most users).
3.  Run the `.msi` installer and click through the prompts.
4.  **IMPORTANT**: Make sure **"Add to PATH"** is checked (it is by default).
5.  After installing, **close and reopen PowerShell**.
6.  Verify with:
    ```powershell
    node --version
    npm --version
    ```

### Start the Dashboard
```powershell
cd C:\Users\user\aureon-trading\frontend
npm install
npm run dev
```
Then open **http://localhost:3000** in your browser.

---

## Step 2: Install Python
Your error `Python was not found` means Python is not installed.

1.  Open the **Microsoft Store** on your computer.
2.  Search for **"Python 3.11"**.
3.  Click **Get** or **Install**.
4.  **IMPORTANT**: When installing, if asked, check the box that says **"Add Python to PATH"**.

## Step 3: Open PowerShell Correctly
1.  Press `Win + X` and select **Windows PowerShell (Admin)** or **Terminal (Admin)**.
2.  You are currently in `C:\WINDOWS\system32`. You need to move to your project folder.

## Step 4: Navigate to the Folder
Type this command and press Enter:
```powershell
cd C:\Users\aureon-trading-main
```
*(If your folder name is different, replace `aureon-trading-main` with the correct name. You can type `cd C:\Users\` and press Tab to see available folders).*

## Step 5: Install Dependencies
Once you are inside the folder (your prompt should look like `PS C:\Users\aureon-trading-main>`), run:

```powershell
pip install -r requirements.txt
```

## Step 6: Run the System
Now you can start the ecosystem using the provided script:

```powershell
.\start_full_ecosystem.ps1
```

---

## Troubleshooting Common Errors

### "The term 'npm' is not recognized" / "The term 'node' is not recognized"
*   **Fix**: Node.js is not installed or not on PATH.
    1.  Download and install from **https://nodejs.org/en/download/** (choose the LTS version).
    2.  Close and reopen PowerShell after installing.
    3.  Verify: `node --version` and `npm --version` should both print version numbers.

### "The term 'pip' is not recognized"
*   **Fix**: This means Python wasn't added to your PATH or you need to restart PowerShell after installing Python. Close the window and open it again.

### "The term 'git' is not recognized"
*   **Fix**: You don't strictly need Git if you downloaded the ZIP file. You can skip git commands.

### "Execution of scripts is disabled on this system"
*   **Fix**: If `.\start_full_ecosystem.ps1` fails, run this command first:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
    Type `Y` when asked.
