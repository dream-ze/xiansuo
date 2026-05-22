import { app, BrowserWindow, Tray, Menu, nativeImage, dialog } from 'electron';
import * as path from 'path';
import * as net from 'net';
import * as fs from 'fs';
import { ProcessManager } from './process-manager';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let processManager: ProcessManager | null = null;
let isQuitting = false;

const APP_PORT = 8001;
const MEDIA_CRAWLER_PORT = 8080;
const APP_HOST = '127.0.0.1';
const APP_URL = `http://${APP_HOST}:${APP_PORT}`;

function getResourcePath(...segments: string[]): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, ...segments);
  }
  return path.join(__dirname, '..', '..', ...segments);
}

function getUserDataPath(...segments: string[]): string {
  return path.join(app.getPath('userData'), ...segments);
}

function firstExistingPath(...paths: string[]): string {
  return paths.find((candidate) => fs.existsSync(candidate)) ?? paths[0];
}

function findPythonDir(): string | undefined {
  const candidates = [
    'D:\\Program Files\\python',
    'C:\\Python312',
    'C:\\Python311',
    'C:\\Python310',
    'C:\\Python39',
    path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python312'),
    path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311'),
    path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310'),
    path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python39'),
  ];
  for (const dir of candidates) {
    if (dir && fs.existsSync(path.join(dir, 'python.exe'))) {
      return dir;
    }
  }
  return undefined;
}

function isPortInUse(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', (err: any) => {
      if (err.code === 'EADDRINUSE') {
        resolve(true);
      } else {
        resolve(false);
      }
    });
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port, '127.0.0.1');
  });
}

function checkBackendHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const http = require('http');
    const req = http.get(`${APP_URL}/health`, (res: any) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

function killProcessOnPort(port: number): Promise<void> {
  return new Promise((resolve) => {
    const { exec } = require('child_process');
    exec(`netstat -ano | findstr ":${port}" | findstr "LISTENING"`, (err: any, stdout: string) => {
      if (err || !stdout.trim()) {
        resolve();
        return;
      }
      const lines = stdout.trim().split('\n');
      const pids = new Set<string>();
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && /^\d+$/.test(pid)) {
          pids.add(pid);
        }
      }
      if (pids.size === 0) {
        resolve();
        return;
      }
      let pending = pids.size;
      for (const pid of pids) {
        exec(`taskkill /PID ${pid} /F`, () => {
          pending--;
          if (pending === 0) resolve();
        });
      }
    });
  });
}

function updateLoadingPage(message: string): void {
  if (!mainWindow) return;
  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(
    `<html><body style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:system-ui;color:#333;">
      <div style="font-size:24px;margin-bottom:16px;">助贷线索雷达</div>
      <div id="status" style="font-size:15px;color:#888;">${message}</div>
      <style>@keyframes spin{to{transform:rotate(360deg)}} .spinner{width:32px;height:32px;border:3px solid #e0e0e0;border-top-color:#1890ff;border-radius:50%;animation:spin .8s linear infinite;margin-bottom:20px;}</style>
      <div class="spinner"></div>
    </body></html>`
  )}`);
}

function showErrorPage(title: string, details: string): void {
  if (!mainWindow) return;
  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(
    `<html><body style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;font-family:system-ui;color:#c00;padding:40px;box-sizing:border-box;">
      <h2>${title}</h2>
      <p style="color:#666;max-width:600px;word-break:break-all;">${details}</p>
    </body></html>`
  )}`);
}

async function prepareDatabase(pm: ProcessManager, pgData: string, installDependencies: boolean, onProgress: (msg: string) => void): Promise<void> {
  const fs = await import('fs/promises');
  const isFirstRun = await fs.access(path.join(pgData, 'PG_VERSION')).then(() => false).catch(() => true);

  if (isFirstRun) {
    onProgress('正在初始化 PostgreSQL 数据目录...');
    await pm.initPostgreSQL(pgData);
  }

  const envPath = getResourcePath('backend', '.env');
  const envExamplePath = getResourcePath('backend', '.env.example');
  try {
    await fs.access(envPath);
  } catch {
    try {
      await fs.access(envExamplePath);
      await fs.copyFile(envExamplePath, envPath);
    } catch {}
  }

  if (installDependencies) {
    onProgress('正在安装 Python 依赖...');
    await pm.installDependencies();
  }

  onProgress('正在启动 PostgreSQL...');
  await pm.startPostgreSQL();

  onProgress('正在创建数据库...');
  await pm.createDatabase();

  onProgress('正在运行数据库迁移...');
  await pm.runMigrations();
}

function getIcon(): Electron.NativeImage {
  const iconPath = getResourcePath('electron', 'assets', 'icon.ico');
  if (fs.existsSync(iconPath)) {
    return nativeImage.createFromPath(iconPath);
  }
  return nativeImage.createEmpty();
}

function createMainWindow(): BrowserWindow {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: '助贷线索雷达',
    show: false,
    icon: getIcon(),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow?.hide();
      const backendReady = mainWindow?.webContents.getURL().includes('127.0.0.1');
      if (!backendReady) {
        isQuitting = true;
        app.quit();
      }
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.on('did-finish-load', () => {
    console.log(`[Electron] Page loaded: ${mainWindow?.webContents.getURL()}`);
  });

  mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDesc) => {
    console.error(`[Electron] Page failed to load: ${errorCode} ${errorDesc}`);
  });

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    console.error(`[Electron] Render process gone: ${details.reason}`);
  });

  mainWindow.webContents.on('console-message', (_event, level, message, line, sourceId) => {
    if (level >= 2) {
      console.error(`[Renderer] ${message} (${sourceId}:${line})`);
    }
  });

  return mainWindow;
}

function createTray(): Tray {
  const icon = getIcon().resize({ width: 16, height: 16 });
  tray = new Tray(icon);
  const contextMenu = Menu.buildFromTemplate([
    { label: '打开主界面', click: () => { mainWindow?.show(); } },
    { type: 'separator' },
    { label: `访问地址: ${APP_URL}`, enabled: false },
    { type: 'separator' },
    { label: '退出', click: () => { isQuitting = true; app.quit(); } },
  ]);
  tray.setToolTip('助贷线索雷达');
  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => { mainWindow?.show(); });
  return tray;
}

function waitForBackend(maxRetries = 60): Promise<boolean> {
  return new Promise((resolve) => {
    let attempts = 0;
    const check = () => {
      checkBackendHealth().then((ok) => {
        if (ok) {
          resolve(true);
        } else {
          attempts++;
          if (attempts >= maxRetries) {
            resolve(false);
          } else {
            setTimeout(check, 1000);
          }
        }
      });
    };
    check();
  });
}

async function startApplication(): Promise<void> {
  const isDev = !app.isPackaged;

  const systemPgDirs = ['16', '15', '14', '17']
    .map(v => path.join('C:\\Program Files\\PostgreSQL', v))
    .filter(d => fs.existsSync(path.join(d, 'bin', 'initdb.exe')));

  const pgDir = isDev
    ? firstExistingPath(
        ...systemPgDirs,
        getResourcePath('tools', 'pgsql'),
        getResourcePath('electron', 'resources', 'tools', 'pgsql'),
        path.join(app.getPath('home'), '.loan-radar', 'pgsql')
      )
    : getResourcePath('tools', 'pgsql');
  const pgData = isDev
    ? firstExistingPath(
        getUserDataPath('pgdata'),
        getResourcePath('data', 'pgdata'),
        getResourcePath('data', 'pgdata_user')
      )
    : getUserDataPath('pgdata');

  const backendDir = getResourcePath('backend');
  const mediacrawlerDir = getResourcePath('mediacrawler');
  const frontendDir = getResourcePath('frontend', 'dist');

  const detectedPythonDir = isDev ? findPythonDir() : undefined;

  processManager = new ProcessManager({
    pgDir,
    pgData,
    pythonCommand: isDev && !detectedPythonDir ? 'python' : undefined,
    pythonDir: isDev ? detectedPythonDir : getResourcePath('tools', 'python'),
    backendDir,
    mediacrawlerDir,
    apisDir: getResourcePath('apis'),
    xhsUtilsDir: getResourcePath('xhs_utils'),
    staticDir: getResourcePath('static'),
    frontendDir,
    port: APP_PORT,
    pgPort: 5432,
    isDev,
  });

  createMainWindow();
  createTray();

  updateLoadingPage('正在启动助贷线索雷达...');
  mainWindow!.show();
  if (isDev) {
    mainWindow!.webContents.openDevTools();
  }

  console.log('[Electron] Starting application...');
  console.log(`[Electron] isDev: ${isDev}`);
  console.log(`[Electron] pgDir: ${pgDir}`);
  console.log(`[Electron] pgData: ${pgData}`);
  console.log(`[Electron] backendDir: ${backendDir}`);
  console.log(`[Electron] frontendDir: ${frontendDir}`);

  updateLoadingPage('正在检查端口占用...');
  const portBusy = await isPortInUse(APP_PORT);
  if (portBusy) {
    const alreadyRunning = await checkBackendHealth();
    if (alreadyRunning) {
      mainWindow?.loadURL(APP_URL);
      return;
    }
    await killProcessOnPort(APP_PORT);
  }

  const mcPortBusy = await isPortInUse(MEDIA_CRAWLER_PORT);
  if (mcPortBusy) {
    await killProcessOnPort(MEDIA_CRAWLER_PORT);
  }

  try {
    await prepareDatabase(processManager, pgData, !isDev, (msg) => {
      console.log(`[Electron] ${msg}`);
      updateLoadingPage(msg);
    });
  } catch (err: any) {
    const errMsg = err?.message || String(err);
    console.error(`[Electron] Database init failed: ${errMsg}`);
    showErrorPage(
      '数据库初始化失败',
      `${errMsg}\n\n请确认 PostgreSQL 组件存在并重试。日志目录: ${pgData}\\..\\pg.log`
    );
    dialog.showErrorBox(
      '数据库初始化失败',
      `${errMsg}\n\n请确认 PostgreSQL 组件存在并重试。`
    );
    return;
  }

  updateLoadingPage('正在启动后端服务...');
  await processManager.startBackend();
  await processManager.startMediaCrawler();

  updateLoadingPage('正在等待后端服务就绪...');
  const backendReady = await waitForBackend();
  console.log(`[Electron] Backend ready: ${backendReady}`);

  if (backendReady) {
    console.log(`[Electron] Loading URL: ${APP_URL}`);
    await mainWindow?.webContents.session.clearCache();
    mainWindow?.loadURL(APP_URL);
  } else {
    showErrorPage(
      '启动超时',
      '后端服务未能及时启动，请检查：<br>• PostgreSQL 是否正在运行<br>• 端口 8001 是否被占用<br><br>关闭窗口后重试，或联系技术支持。'
    );
  }
}

app.on('ready', () => {
  startApplication().catch((err) => {
    dialog.showErrorBox('启动失败', `${err}`);
    app.quit();
  });
});

app.on('before-quit', () => {
  isQuitting = true;
  if (processManager) {
    processManager.stopAll().catch(() => {});
  }
});

app.on('window-all-closed', () => {
});
