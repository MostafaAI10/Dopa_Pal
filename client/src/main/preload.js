const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  moveWindow     : (dx, dy) => ipcRenderer.send('move-window', dx, dy),
  resizeBubble   : (w, h)   => ipcRenderer.send('resize-bubble', w, h),
  openDashboard  : ()       => ipcRenderer.send('open-dashboard'),
  closeDashboard : ()       => ipcRenderer.send('close-dashboard'),
  maximizeDashboard: ()     => ipcRenderer.send('maximize-dashboard'),
  minimizeDashboard: ()     => ipcRenderer.send('minimize-dashboard'),
  createTask     : (payload)    => ipcRenderer.invoke('create-task', payload),
  updateTask     : (id, payload) => ipcRenderer.invoke('update-task', id, payload),
  ingestTask     : (payload)    => ipcRenderer.invoke('ingest-task', payload),
  ingestVoiceTask: (audioBuffer)=> ipcRenderer.invoke('ingest-voice-task', audioBuffer),
  openBubbleAddMenu: () => ipcRenderer.send('open-bubble-add-menu'),
  onDashboardRefresh: (callback) => ipcRenderer.on('dashboard-refresh', callback),
  onOpenAddMenu: (callback) => ipcRenderer.on('open-add-menu', callback),
  setIgnoreMouse: (ignore) => ipcRenderer.send('set-ignore-mouse', ignore),
});
