const path = require('node:path');
const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { RuntimeManager, WEB_URL, RUNTIME_URL } = require('./runtime-manager.cjs');

const runtimeManager = new RuntimeManager();
let mainWindow = null;

function isAllowedExternalUrl(rawUrl) {
  try {
    const parsed = new URL(String(rawUrl || ''));
    if (!['http:', 'https:'].includes(parsed.protocol)) return false;
    if (['127.0.0.1', 'localhost', '::1'].includes(parsed.hostname)) return true;
    const allowedHosts = String(process.env.FLAMEBORN_DESKTOP_ALLOWED_EXTERNAL_HOSTS || '')
      .split(',')
      .map((host) => host.trim().toLowerCase())
      .filter(Boolean);
    return allowedHosts.includes(parsed.hostname.toLowerCase());
  } catch {
    return false;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 1100,
    minHeight: 720,
    title: 'FlameBorn Academy Desktop',
    backgroundColor: '#05080d',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadURL(WEB_URL);
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    return isAllowedExternalUrl(url) ? { action: 'allow' } : { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url !== WEB_URL && !isAllowedExternalUrl(url)) {
      event.preventDefault();
    }
  });

  if (process.env.FLAMEBORN_DESKTOP_DEVTOOLS === 'true') {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

ipcMain.handle('flameborn:get-status', async () => {
  return runtimeManager.getStatus();
});

ipcMain.handle('flameborn:restart-service', async (_event, name) => {
  return runtimeManager.restartService(name);
});

ipcMain.handle('flameborn:open-path', async (_event, targetPath) => {
  if (!targetPath || typeof targetPath !== 'string') return false;
  const result = await shell.openPath(targetPath);
  return result === '';
});

ipcMain.handle('flameborn:open-external', async (_event, url) => {
  if (!url || typeof url !== 'string') return false;
  if (!isAllowedExternalUrl(url)) return false;
  await shell.openExternal(url);
  return true;
});

app.whenReady().then(async () => {
  const status = await runtimeManager.ensureServices();
  const webReachable = Boolean(status.services?.web?.reachable);
  const runtimeReachable = Boolean(status.services?.runtime?.reachable);
  if (!webReachable || !runtimeReachable) {
    await dialog.showErrorBox(
      'FlameBorn startup error',
      [
        `Web UI reachable: ${webReachable}`,
        `Runtime reachable: ${runtimeReachable}`,
        `Expected web: ${WEB_URL}`,
        `Expected runtime: ${RUNTIME_URL}`,
        '',
        'Check logs in logs/desktop/ and start services manually if needed.',
      ].join('\n')
    );
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  runtimeManager.shutdown();
});
