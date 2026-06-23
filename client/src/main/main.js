import { app, BrowserWindow, ipcMain, screen, globalShortcut, clipboard, Notification } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { exec } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);


let bubbleWin    = null;
let dashboardWin = null;

const API_BASE_URL = process.env.DOPAPAL_API_BASE_URL || 'http://localhost:8000/api/v1';
const apiUrl = (route) => `${API_BASE_URL}${route}`;

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

/* ── IPC: Get current window position (used at drag start) ── */
ipcMain.handle('get-window-position', () => {
  if (!bubbleWin) return { x: 0, y: 0 };
  const [x, y] = bubbleWin.getPosition();
  return { x, y };
});

/* ── IPC: Set window position (drag) ───────────────────── */
ipcMain.on('set-window-position', (_e, x, y) => {
  if (!bubbleWin) return;
  bubbleWin.setPosition(Math.round(x), Math.round(y));
});

/* ── IPC: Move window by delta (legacy) ───────────────── */
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
    const response = await fetch(apiUrl('/tasks/create'), {
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
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } catch (e) { }
      throw new Error("Backend API error: " + errorDetail);
    }
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
    const response = await fetch(apiUrl('/tasks/ingest'), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_text: payload.source_text,
        source_type: payload.source_type
      })
    });
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } catch (e) { }
      throw new Error("Backend API error: " + errorDetail);
    }
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
    const response = await fetch(apiUrl(`/tasks/${id}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } catch (e) { }
      throw new Error("Backend API error: " + errorDetail);
    }
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
    // Create multipart form data for streaming upload
    const FormData = (await import('form-data')).default;
    const formData = new FormData();
    
    // Append the audio buffer as a file
    formData.append('file', Buffer.from(audioBuffer), {
      filename: 'voice_recording.webm',
      contentType: 'audio/webm'
    });
    formData.append('source_type', 'voice');
    
    // Send to backend voice ingestion endpoint using multipart/form-data
    const response = await fetch(apiUrl('/tasks/ingest-voice'), {
      method: "POST",
      body: formData,
      // Don't set Content-Type header - fetch will set it with the boundary
    });
    
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } catch (e) {
        // ignore
      }
      throw new Error(`Backend API error: ${errorDetail}`);
    }
    
    const json = await response.json();
    
    // Refresh dashboard if open
    if (dashboardWin) {
      dashboardWin.webContents.send('dashboard-refresh');
    }
    
    return json;
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
      const response = await fetch(apiUrl('/tasks'));
      if (!response.ok) return;
      const tasks = await response.json();
      
      const pendingTasks = tasks.filter(t => t.status !== 'completed');
      
      // 1. Check for High Priority tasks
      const highPriority = pendingTasks.filter(t => t.priority === 'high');
      for (const t of highPriority) {
        if (!lastNotifiedTasks.has(t.id)) {
          // Use enhanced notification service
          await enhancedElectronNotificationService.createEnhancedNotification({
            title: '⚠️ High Priority Task Pending!',
            body: `Don't forget: "${t.title}" needs your attention. Estimated time: ${t.duration_minutes || 15} min.`,
            icon: '⚠️',
            audio_file: 'warning',
            priority: 'high',
            metadata: {
              task_id: t.id,
              task_title: t.title,
              duration_minutes: t.duration_minutes || 15
            }
          });
          lastNotifiedTasks.add(t.id);
        }
      }

      // 2. Daily reminder logic (cooldown: 10 minutes for demo)
      const now = Date.now();
      if (pendingTasks.length > 0 && now - lastDailyReminder > 600000) { 
        // Use enhanced notification service
        await enhancedElectronNotificationService.createEnhancedNotification({
          title: '👋 DopaPal Reminder',
          body: `You have ${pendingTasks.length} pending tasks. Don't forget to follow up on your goals today!`,
          icon: '👋',
          audio_file: 'notification',
          priority: 'normal',
          metadata: {
            task_count: pendingTasks.length,
            reminder_type: 'daily'
          }
        });
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
  // Global shortcut to capture currently highlighted text anywhere in the OS
  globalShortcut.register('CommandOrControl+Shift+Space', async () => {
    // 1. Save old clipboard
    const oldText = clipboard.readText();
    
    // Wait briefly to allow the user to physically release the shortcut keys (Ctrl/Shift/Space)
    // Otherwise, the OS might interpret the simulated Ctrl+C as Ctrl+Shift+C.
    setTimeout(() => {
      clipboard.clear(); // Clear clipboard to reliably detect when the copy succeeds
      
      // 2. Simulate Ctrl+C to copy the highlighted text
      exec('powershell.exe -command "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys(\'^c\')"', async () => {
        
        let retries = 10;
        const checkClipboard = async () => {
          const newText = clipboard.readText();
          
          if (newText && newText !== '') {
            // Restore old clipboard immediately so user doesn't lose their data
            clipboard.writeText(oldText);
            
            new Notification({ title: 'DopaPal', body: 'Highlight captured! Analyzing with AI...' }).show();

            try {
              // 3. Process with AI via Backend
              const response = await fetch(apiUrl('/tasks/ingest'), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  source_text: newText,
                  source_type: 'highlight'
                })
              });
              
              if (!response.ok) {
                let errorDetail = "Backend API error";
                try {
                  const errJson = await response.json();
                  if (errJson.detail) errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
                } catch (e) { }
                throw new Error(errorDetail);
              }
              const parsed = await response.json();

              // 4. Show success notification
              new Notification({
                title: '✅ AI Task Saved!',
                body: `Extracted from highlight: "${parsed.title}"`
              }).show();
                  
              // 5. Refresh dashboard if open
              if (dashboardWin && !dashboardWin.isDestroyed()) {
                  dashboardWin.webContents.send('dashboard-refresh');
              }
            } catch (error) {
              console.error("Failed to process hotkey task:", error);
              new Notification({
                title: '❌ DopaPal Error',
                body: 'Failed to extract task. Ensure backend is running.'
              }).show();
            }
          } else if (retries > 0) {
            retries--;
            setTimeout(checkClipboard, 50); // Poll every 50ms
          } else {
            // Restore old clipboard and fail
            if (oldText) clipboard.writeText(oldText);
            new Notification({ title: 'DopaPal', body: 'Could not capture highlight. Make sure text is selected.' }).show();
          }
        };
        
        checkClipboard();
      });
    }, 400); // 400ms delay before sending keystroke
  });
};

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
