import { app, BrowserWindow, ipcMain, screen, globalShortcut, clipboard, Notification } from 'electron';
import { exec } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);


let bubbleWin    = null;
let dashboardWin = null;

const ICON_W = 80;
const ICON_H = 80;

/* ── Bubble window ─────────────────────────────────────── */
const createBubble = () => {
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  // We use a fixed large transparent window to avoid the OS-level window resize jitter
  const FIXED_W = 360;
  const FIXED_H = 540;

  bubbleWin = new BrowserWindow({
    width : FIXED_W,
    height: FIXED_H,
    x: sw - FIXED_W - 24,
    y: sh - FIXED_H - 24,
    transparent: true,
    frame      : false,
    alwaysOnTop: true,
    resizable  : false,
    movable    : true,
    hasShadow  : false,
    webPreferences: {
      preload        : path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  const url = process.env.VITE_DEV_SERVER_URL;
  if (url) bubbleWin.loadURL(url + '#/');
  else     bubbleWin.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/' });
};

/* ── Dashboard window ──────────────────────────────────── */
const createDashboard = () => {
  if (dashboardWin) { dashboardWin.focus(); return; }

  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  dashboardWin = new BrowserWindow({
    width : Math.min(1100, sw - 80),
    height: Math.min(700,  sh - 80),
    minWidth : 800,
    minHeight: 560,
    center: true,
    frame      : false,
    resizable  : true,
    alwaysOnTop: false,
    webPreferences: {
      preload        : path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  const url = process.env.VITE_DEV_SERVER_URL;
  if (url) dashboardWin.loadURL(url + '#/dashboard');
  else     dashboardWin.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/dashboard' });

  // ★ Hide bubble when dashboard opens
  if (bubbleWin) bubbleWin.hide();

  dashboardWin.on('closed', () => {
    dashboardWin = null;
    // ★ Show bubble again when dashboard closes
    if (bubbleWin) {
      bubbleWin.show();
      bubbleWin.setAlwaysOnTop(true);
    }
  });
};

/* ── IPC: Move window by delta (drag) ──────────────────── */
ipcMain.on('move-window', (_e, dx, dy) => {
  if (!bubbleWin) return;
  const [x, y] = bubbleWin.getPosition();
  bubbleWin.setPosition(Math.round(x + dx), Math.round(y + dy));
});

/* ── IPC: Dashboard ────────────────────────────────────── */
ipcMain.on('open-dashboard',  () => createDashboard());
ipcMain.on('open-bubble-add-menu', () => {
  if (bubbleWin) {
    bubbleWin.show();
    bubbleWin.webContents.send('open-add-menu');
  }
});
ipcMain.on('close-dashboard', () => { if (dashboardWin) dashboardWin.close(); });
ipcMain.on('maximize-dashboard', () => {
  if (dashboardWin) {
    if (dashboardWin.isMaximized()) {
      dashboardWin.unmaximize();
    } else {
      dashboardWin.maximize();
    }
  }
});
ipcMain.on('minimize-dashboard', () => {
  if (dashboardWin) dashboardWin.minimize();
});

/* ── IPC: Tasks ────────────────────────────────────────── */
ipcMain.handle('create-task', async (_e, payload) => {
  try {
    const response = await fetch("http://localhost:8000/api/v1/tasks/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: payload.title,
        deadline: payload.deadline ? new Date(payload.deadline).toISOString() : null,
        estimated_hours: payload.estimatedHours || 2.0,
        interest_tag: payload.interestTag || null,
        source_type: payload.sourceType || 'manual'
      })
    });
    if (!response.ok) throw new Error("Backend API error: " + response.statusText);
    const json = await response.json();
    if (dashboardWin) dashboardWin.webContents.send('dashboard-refresh');
    return json;
  } catch (error) {
    console.error('Error creating task:', error);
    throw error;
  }
});

ipcMain.handle('ingest-task', async (_e, payload) => {
  try {
    const response = await fetch("http://localhost:8000/api/v1/tasks/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_text: payload.source_text,
        source_type: payload.source_type
      })
    });
    if (!response.ok) throw new Error("Backend API error: " + response.statusText);
    const json = await response.json();
    if (dashboardWin) dashboardWin.webContents.send('dashboard-refresh');
    return json;
  } catch (error) {
    console.error('Error ingesting task:', error);
    throw error;
  }
});

ipcMain.handle('update-task', async (_e, id, payload) => {
  try {
    const response = await fetch(`http://localhost:8000/api/v1/tasks/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error("Backend API error: " + response.statusText);
    const json = await response.json();
    if (dashboardWin) dashboardWin.webContents.send('dashboard-refresh');
    return json;
  } catch (error) {
    console.error('Error updating task:', error);
    throw error;
  }
});

ipcMain.handle('ingest-voice-task', async (_e, audioBuffer) => {
  try {
    // Note: If you have a specific voice ingest endpoint, call it here.
    // For now, mapping voice to ingest if it's text, or if audio processing is elsewhere.
    // Assuming the backend has a /tasks/ingest that handles voice or it's not implemented yet.
    throw new Error("Voice ingest to backend not fully implemented in this hackathon version.");
  } catch (error) {
    console.error('Error ingesting voice task:', error);
    throw error;
  }
});

ipcMain.on('set-ignore-mouse', (_e, ignore) => {
  if (bubbleWin) {
    bubbleWin.setIgnoreMouseEvents(ignore, { forward: true });
  }
});

/* ── App lifecycle ─────────────────────────────────────── */
app.on('second-instance', () => {
  // If second instance tries to open, focus the dashboard or bubble
  if (dashboardWin) dashboardWin.focus();
  else if (bubbleWin) bubbleWin.show();
});

let lastNotifiedTasks = new Set();
let lastDailyReminder = 0;

const startNotificationSystem = () => {
  // Run every 1 minute for testing purposes
  setInterval(async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/tasks");
      if (!response.ok) return;
      const tasks = await response.json();
      
      const pendingTasks = tasks.filter(t => t.status !== 'completed');
      
      // 1. Check for High Priority tasks
      const highPriority = pendingTasks.filter(t => t.priority === 'high');
      for (const t of highPriority) {
        if (!lastNotifiedTasks.has(t.id)) {
          new Notification({
            title: '⚠️ High Priority Task Pending!',
            body: `Don't forget: "${t.title}" needs your attention. Estimated time: ${t.duration_minutes || 15} min.`
          }).show();
          lastNotifiedTasks.add(t.id);
        }
      }

      // 2. Daily reminder logic (cooldown: 10 minutes for demo)
      const now = Date.now();
      if (pendingTasks.length > 0 && now - lastDailyReminder > 600000) { 
        new Notification({
          title: '👋 DopaPal Reminder',
          body: `You have ${pendingTasks.length} pending tasks. Don't forget to follow up on your goals today!`
        }).show();
        lastDailyReminder = now;
      }
    } catch (e) {
      // Backend might be offline, ignore silently
    }
  }, 60000); // 1 minute interval
};

// Required for Notifications to work on Windows 10/11
app.setAppUserModelId('com.dopapal.app');

app.whenReady().then(() => {
  if (process.platform === 'win32') {
    app.setAppUserModelId('DopaPal.App');
  }
  createBubble();
  startNotificationSystem();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createBubble();
  });
  registerGlobalShortcuts();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

const registerGlobalShortcuts = () => {
  // Use Ctrl+Alt+A to avoid Windows shortcut conflicts
  globalShortcut.register('CommandOrControl+Alt+A', async () => {
    // 1. Read what the user already copied to their clipboard
    const newText = clipboard.readText();
        
    if (!newText || newText.trim() === '') {
      new Notification({ title: 'DopaPal', body: 'Clipboard is empty. Please copy some text first (Ctrl+C).' }).show();
      return;
    }

    try {
      // 2. Process with AI via Backend
      const response = await fetch("http://localhost:8000/api/v1/tasks/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_text: newText,
          source_type: 'ai'
        })
      });
      
      if (!response.ok) throw new Error("Backend API error");
      const parsed = await response.json();

      // 3. Show success notification
      new Notification({
        title: '✅ AI Task Saved!',
        body: `Added: "${parsed.title}"`
      }).show();
          
      // 4. Refresh dashboard if open
      if (dashboardWin && !dashboardWin.isDestroyed()) {
          dashboardWin.webContents.reload();
      }
    } catch (error) {
      console.error("Failed to process hotkey task:", error);
      new Notification({
        title: '❌ DopaPal Error',
        body: 'Failed to extract task. Ensure API key is valid.'
      }).show();
    }
  });
};

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
