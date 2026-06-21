import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import api from '../../services/api';
import { useLanguage } from '../../contexts/LanguageContext';

/* ─── Helpers ───────────────────────────────────────────── */
const IS_ELECTRON = typeof window !== 'undefined' && !!window.electronAPI;

/* ─── Mock data (replace with real API later) ───────────── */
const USER = {
  name  : 'Anchor User',
  email : 'user@anchor.app',
  avatar: '🧠',
  streak: 7,
  level : 'Focus Apprentice',
  xp    : 340,
  xpMax : 500,
};

const TASKS = [
  { id: 1, title: 'Review project proposal', due: 'Today',    priority: 'high',   done: false },
  { id: 2, title: 'Reply to team emails',     due: 'Today',    priority: 'medium', done: false },
  { id: 3, title: 'Read chapter 3 of book',  due: 'Tomorrow', priority: 'low',    done: false },
  { id: 4, title: 'Weekly planning session',  due: 'Today',    priority: 'high',   done: true  },
  { id: 5, title: 'Update progress tracker',  due: 'This week',priority: 'medium', done: true  },
];

const RECOMMEND = {
  title  : 'Reply to team emails',
  reason : 'You tend to work best on communication tasks in the evening. This has been waiting 2 days.',
  energy : 'Low',
  time   : '15 min',
};

/* ─── Icons ─────────────────────────────────────────────── */
const Svg = ({ children, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);
const IconHome     = () => <Svg><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></Svg>;
const IconTask     = () => <Svg><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></Svg>;
const IconUser     = () => <Svg><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></Svg>;
const IconSparkle  = () => <Svg><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z"/></Svg>;
const IconMaximize = () => <Svg><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></Svg>;
const IconClose    = () => <Svg><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></Svg>;
const IconCheck    = () => <Svg size={16}><polyline points="20 6 9 17 4 12"/></Svg>;
const IconEdit     = () => <Svg size={16}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></Svg>;
const IconTrash    = () => <Svg size={16}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></Svg>;
const IconPlus     = () => <Svg><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></Svg>;
const IconMinus    = () => <Svg><line x1="5" y1="12" x2="19" y2="12"/></Svg>;
const IconMic      = () => <Svg><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></Svg>;
const IconKeyboard = () => <Svg><rect width="20" height="16" x="2" y="4" rx="2" ry="2"/><line x1="6" x2="6.01" y1="8" y2="8"/><line x1="10" x2="10.01" y1="8" y2="8"/><line x1="14" x2="14.01" y1="8" y2="8"/><line x1="18" x2="18.01" y1="8" y2="8"/><line x1="8" x2="16" y1="12" y2="12"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/><line x1="14" x2="14.01" y1="16" y2="16"/><line x1="18" x2="18.01" y1="16" y2="16"/></Svg>;
const IconFire     = () => <Svg><path d="M12 2c0 0-5 5-5 10a5 5 0 0 0 10 0C17 7 12 2 12 2z"/></Svg>;
const IconSettings = () => <Svg><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></Svg>;
const IconLink     = () => <Svg><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3A5 5 0 0 0 11 21.07l1.71-1.71"/></Svg>;
const IconShop     = () => <Svg><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></Svg>;
const IconSync     = () => <Svg><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 21v-5h5"/><path d="M3 12A9 9 0 0 1 18.5 5.7L21 8"/><path d="M21 3v5h-5"/></Svg>;
const IconMusic    = () => <Svg><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></Svg>;

/* ─── Themes Store ──────────────────────────────────────── */
const THEMES = [
  { id: 'default', name: 'Dopa Default', cost: 0, accent: '#a78bfa', glow: 'rgba(167,139,250,.35)', dim: 'rgba(167,139,250,.12)' },
  { id: 'ocean', name: 'Ocean Breeze', cost: 500, accent: '#38bdf8', glow: 'rgba(56,189,248,.35)', dim: 'rgba(56,189,248,.12)' },
  { id: 'sunset', name: 'Sunset Flare', cost: 1500, accent: '#f97316', glow: 'rgba(249,115,22,.35)', dim: 'rgba(249,115,22,.12)' },
  { id: 'cyber', name: 'Neon Cyberpunk', cost: 3000, accent: '#ec4899', glow: 'rgba(236,72,153,.35)', dim: 'rgba(236,72,153,.12)' },
  { id: 'gold', name: 'Midnight Gold', cost: 10000, accent: '#fbbf24', glow: 'rgba(251,191,36,.35)', dim: 'rgba(251,191,36,.12)' },
];

const SHOP_ITEMS = [
  { id: 'music-lofi', type: 'Music', name: 'Lo-fi Focus Loop', cost: 800, accent: '#38bdf8', description: 'Soft study ambience for deep work sessions.' },
  { id: 'music-rain', type: 'Music', name: 'Rain Desk', cost: 1200, accent: '#34d399', description: 'Gentle rain bed for the bubble and dashboard.' },
  { id: 'visual-glass', type: 'Visual', name: 'Frosted Panels', cost: 900, accent: '#f472b6', description: 'Adds a brighter glass treatment to panels.' },
  { id: 'visual-compact', type: 'Visual', name: 'Compact Mode', cost: 600, accent: '#fbbf24', description: 'Tighter spacing for dense planning days.' },
];

const LANGUAGE_OPTIONS = [
  { code: 'ar', label: 'Arabic', native: 'العربية', dir: 'rtl', region: 'MENA' },
  { code: 'en', label: 'English', native: 'English', dir: 'ltr', region: 'Global' },
  { code: 'fr', label: 'French', native: 'Français', dir: 'ltr', region: 'Europe' },
  { code: 'es', label: 'Spanish', native: 'Español', dir: 'ltr', region: 'LatAm / Europe' },
  { code: 'de', label: 'German', native: 'Deutsch', dir: 'ltr', region: 'Europe' },
  { code: 'tr', label: 'Turkish', native: 'Türkçe', dir: 'ltr', region: 'Turkey' },
  { code: 'fa', label: 'Persian', native: 'فارسی', dir: 'rtl', region: 'Iran' },
  { code: 'ur', label: 'Urdu', native: 'اردو', dir: 'rtl', region: 'Pakistan' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी', dir: 'ltr', region: 'India' },
  { code: 'ja', label: 'Japanese', native: '日本語', dir: 'ltr', region: 'Japan' },
  { code: 'zh', label: 'Chinese', native: '中文', dir: 'ltr', region: 'China' },
];

const NOTIFICATION_LEVELS = [
  { id: 'off', label: 'Off', detail: 'No proactive alerts' },
  { id: 'essentials', label: 'Essentials', detail: 'Deadlines, completions, critical sync' },
  { id: 'balanced', label: 'Balanced', detail: 'Essential plus reminders and summaries' },
  { id: 'high-touch', label: 'High Touch', detail: 'Frequent prompts, nudges, and digest' },
];

const NOTIFICATION_CHANNELS = [
  { id: 'in_app', label: 'In-app' },
  { id: 'push', label: 'Push' },
  { id: 'email', label: 'Email' },
  { id: 'sound', label: 'Sound' },
];

const NOTIFICATION_CATEGORIES = [
  { id: 'deadlines', label: 'Deadlines' },
  { id: 'streaks', label: 'Streaks' },
  { id: 'sync', label: 'Sync updates' },
  { id: 'rewards', label: 'Rewards' },
  { id: 'daily_digest', label: 'Daily digest' },
  { id: 'focus_bursts', label: 'Focus bursts' },
];

const NOTIFICATION_DIGESTS = [
  { id: 'none', label: 'Never' },
  { id: 'daily', label: 'Daily' },
  { id: 'weekdays', label: 'Weekdays' },
  { id: 'weekly', label: 'Weekly' },
];

const INTEGRATION_PROVIDERS = [
  { id: 'google', name: 'Google Calendar', accent: '#38bdf8', tokenLabel: 'OAuth access token', settingLabel: 'Calendar ID', settingKey: 'calendar_id' },
  { id: 'notion', name: 'Notion', accent: '#f8fafc', tokenLabel: 'Integration token', settingLabel: 'Database ID', settingKey: 'database_id' },
  { id: 'jira', name: 'Jira', accent: '#60a5fa', tokenLabel: 'API token', settingLabel: 'Project key', settingKey: 'project_key' },
  { id: 'canvas', name: 'Canvas LMS', accent: '#fb7185', tokenLabel: 'Access token', settingLabel: 'Course ID', settingKey: 'course_id' },
];

/* ─── Priority badge ────────────────────────────────────── */
const PriorityBadge = ({ level }) => (
  <span className={`d-badge d-badge--${level}`}>{level.toUpperCase()}</span>
);

/* ─── Task row ──────────────────────────────────────────── */
const TaskRow = ({ task, onToggle, onDelete, onUpdateTask }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editPriority, setEditPriority] = useState(task.priority);
  const [editDeadline, setEditDeadline] = useState(
    task.deadlineRaw ? new Date(task.deadlineRaw).toISOString().slice(0, 16) : ''
  );
  const [editDuration, setEditDuration] = useState(task.estimatedHours ?? '');

  const handleSave = () => {
    onUpdateTask(task.id, {
      title: editTitle,
      priority: editPriority,
      deadline: editDeadline ? new Date(editDeadline).toISOString() : undefined,
      estimatedHours: editDuration !== '' ? parseFloat(editDuration) : undefined,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditTitle(task.title);
    setEditPriority(task.priority);
    setEditDeadline(task.deadlineRaw ? new Date(task.deadlineRaw).toISOString().slice(0, 16) : '');
    setEditDuration(task.estimatedHours ?? '');
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="d-task d-task--editing" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '10px', background: 'rgba(167,139,250,0.06)', borderColor: 'var(--accent)', padding: '14px 16px' }}>
        {/* Row 1: Title + Priority */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="text"
            value={editTitle}
            onChange={e => setEditTitle(e.target.value)}
            className="d-input"
            placeholder="Task title"
            style={{ flex: 1, padding: '6px 10px', fontSize: '14px', margin: 0, height: 'auto' }}
            autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') handleCancel(); }}
          />
          <select
            value={editPriority}
            onChange={e => setEditPriority(e.target.value)}
            className={`d-badge d-badge--${editPriority}`}
            style={{ cursor: 'pointer', outline: 'none', border: '1px solid rgba(255,255,255,0.2)', padding: '4px 10px', flexShrink: 0 }}
          >
            <option style={{color: 'black'}} value="high">HIGH</option>
            <option style={{color: 'black'}} value="medium">MEDIUM</option>
            <option style={{color: 'black'}} value="low">LOW</option>
          </select>
        </div>
        {/* Row 2: Deadline + Duration */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>📅 Deadline</label>
            <input
              type="datetime-local"
              value={editDeadline}
              onChange={e => setEditDeadline(e.target.value)}
              className="d-input"
              style={{ padding: '6px 10px', fontSize: '13px', margin: 0, height: 'auto', colorScheme: 'dark' }}
            />
          </div>
          <div style={{ width: '130px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>⏱️ Duration (hrs)</label>
            <input
              type="number"
              min="0.25"
              max="200"
              step="0.25"
              value={editDuration}
              onChange={e => setEditDuration(e.target.value)}
              className="d-input"
              placeholder="e.g. 2.5"
              style={{ padding: '6px 10px', fontSize: '13px', margin: 0, height: 'auto' }}
            />
          </div>
        </div>
        {/* Row 3: Actions */}
        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
          <button onClick={handleSave} className="d-btn d-btn--primary" style={{ padding: '6px 16px', minWidth: 'auto', fontSize: '13px', gap: 0 }}>✓ Save</button>
          <button onClick={handleCancel} className="d-btn d-btn--secondary" style={{ padding: '6px 16px', minWidth: 'auto', fontSize: '13px', gap: 0 }}>✕ Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`d-task${task.done ? ' d-task--done' : ''}`}>
      <button className={`d-task-check${task.done ? ' checked' : ''}`} onClick={() => onToggle(task.id)}>
        {task.done && <IconCheck />}
      </button>
      <div className="d-task-body">
        <span className="d-task-title">{task.title}</span>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="d-task-due">📅 {task.due}</span>
          {task.estimatedHours != null && (
            <span className="d-task-due">⏱️ {task.estimatedHours}h</span>
          )}
        </div>
      </div>
      <PriorityBadge level={task.priority} />
      {!task.done && (
        <button className="d-task-edit" onClick={() => setIsEditing(true)} style={{ background: 'none', border: 'none', color: '#a78bfa', cursor: 'pointer', marginLeft: '12px', padding: 0, display: 'flex' }} title="Edit Task">
          <IconEdit />
        </button>
      )}
      <button className="d-task-delete" onClick={() => onDelete(task.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', marginLeft: '12px', padding: 0, display: 'flex' }} title="Delete Task">
        <IconTrash />
      </button>
    </div>
  );
};

/* ══════════════════════════════════════════════════════════
   DASHBOARD COMPONENT
   ══════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const { t, lang, changeLanguage, isRTL } = useLanguage();
  const chatEndRef = useRef(null);
  const [tab,   setTab]   = useState('home');
  const [tasks, setTasks] = useState([]);
  const [bubbleTask, setBubbleTask] = useState(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState([
    { sender: 'ai', text: 'Hello! I am DopaPal, your personal AI focus assistant. How can I help you today?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  // Profile state
  const [userName, setUserName] = useState('Anchor User');
  const [isEditingName, setIsEditingName] = useState(false);
  const [accountForm, setAccountForm] = useState({
    name: 'Anchor User',
    wakeTimePref: '07:30',
  });

  // Add Task Modal State
  const [showAddTaskModal, setShowAddTaskModal] = useState(false);
  const [addTaskView, setAddTaskView] = useState('options'); // 'options', 'manual', 'ai', 'voice'
  const [taskData, setTaskData] = useState({ title: '', duration: '', due: '', notes: '' });
  const [aiText, setAiText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmittingTask, setIsSubmittingTask] = useState(false);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);

  // Theme state
  const [userXp, setUserXp] = useState(0);
  const [unlockedThemes, setUnlockedThemes] = useState(['default']);
  const [unlockedShopItems, setUnlockedShopItems] = useState([]);
  const [activeTheme, setActiveTheme] = useState('default');
  const [activeMusic, setActiveMusic] = useState('none');
  const [activeVisual, setActiveVisual] = useState('default');
  const [purchaseError, setPurchaseError] = useState(null);

  // Integration state
  const [integrationStatuses, setIntegrationStatuses] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('google');
  const [integrationForm, setIntegrationForm] = useState({
    accessToken: '',
    refreshToken: '',
    expiresInSeconds: 3600,
    settingValue: '',
  });
  const [integrationSaving, setIntegrationSaving] = useState(false);
  const [integrationMessage, setIntegrationMessage] = useState('');

  // Settings state
  const [languageDraft, setLanguageDraft] = useState({
    primary: 'ar',
    secondary: 'en',
    contentMode: 'auto',
    transliteration: false,
    dateFormat: 'locale',
    numberFormat: 'locale',
  });
  const [notificationDraft, setNotificationDraft] = useState({
    level: 'balanced',
    channels: ['in_app', 'sound'],
    categories: ['deadlines', 'streaks', 'rewards'],
    digest: 'daily',
    quietStart: '21:00',
    quietEnd: '08:00',
    soundProfile: 'soft',
  });
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState('');
  const [settingsSection, setSettingsSection] = useState('account');

  // Streak & gamification state
  const [streak, setStreak] = useState(0);
  const [streakEmoji, setStreakEmoji] = useState('🔥');
  const [streakAnim, setStreakAnim] = useState('');
  const [floatingEmojis, setFloatingEmojis] = useState([]);

  useEffect(() => {
    const savedXp = localStorage.getItem('dopapal_xp_v3');
    if (savedXp) setUserXp(parseInt(savedXp, 10));
    else localStorage.setItem('dopapal_xp_v3', 0);

    const savedUnlocked = localStorage.getItem('dopapal_themes_v3');
    if (savedUnlocked) setUnlockedThemes(JSON.parse(savedUnlocked));

    const savedShopItems = localStorage.getItem('dopapal_shop_items_v1');
    if (savedShopItems) setUnlockedShopItems(JSON.parse(savedShopItems));

    const savedActive = localStorage.getItem('dopapal_active_theme_v3');
    if (savedActive) setActiveTheme(savedActive);

    const savedMusic = localStorage.getItem('dopapal_active_music_v1');
    if (savedMusic) setActiveMusic(savedMusic);

    const savedVisual = localStorage.getItem('dopapal_active_visual_v1');
    if (savedVisual) setActiveVisual(savedVisual);
    
    const savedStreak = localStorage.getItem('dopapal_streak_v3');
    if (savedStreak) setStreak(parseInt(savedStreak, 10));

    const savedName = localStorage.getItem('dopapal_username');
    if (savedName) setUserName(savedName);

    const savedLanguageDraft = localStorage.getItem('dopapal_language_prefs_v1');
    if (savedLanguageDraft) {
      try {
        setLanguageDraft(prev => ({ ...prev, ...JSON.parse(savedLanguageDraft) }));
      } catch {
        // ignore malformed local draft
      }
    }

    const savedNotificationDraft = localStorage.getItem('dopapal_notification_prefs_v1');
    if (savedNotificationDraft) {
      try {
        setNotificationDraft(prev => ({ ...prev, ...JSON.parse(savedNotificationDraft) }));
      } catch {
        // ignore malformed local draft
      }
    }

    const savedWake = localStorage.getItem('dopapal_wake_time_v1');
    if (savedWake) {
      setAccountForm(prev => ({ ...prev, wakeTimePref: savedWake }));
    }
  }, []);

  useEffect(() => {
    const theme = THEMES.find(t => t.id === activeTheme) || THEMES[0];
    document.documentElement.style.setProperty('--accent', theme.accent);
    document.documentElement.style.setProperty('--accent-glow', theme.glow);
    document.documentElement.style.setProperty('--accent-dim', theme.dim);
  }, [activeTheme]);

  const buyTheme = (themeId, cost) => {
    if (userXp >= cost && !unlockedThemes.includes(themeId)) {
        const newXp = userXp - cost;
        const newUnlocked = [...unlockedThemes, themeId];
        setUserXp(newXp);
        setUnlockedThemes(newUnlocked);
        localStorage.setItem('dopapal_xp_v3', newXp);
        localStorage.setItem('dopapal_themes_v3', JSON.stringify(newUnlocked));
        setPurchaseError(null);
    } else if (userXp < cost) {
        setPurchaseError('Not enough XP to unlock this theme!');
        setTimeout(() => setPurchaseError(null), 3000);
    }
  };

  const buyShopItem = (itemId, cost) => {
    if (userXp >= cost && !unlockedShopItems.includes(itemId)) {
      const newXp = userXp - cost;
      const newUnlocked = [...unlockedShopItems, itemId];
      setUserXp(newXp);
      setUnlockedShopItems(newUnlocked);
      localStorage.setItem('dopapal_xp_v3', newXp);
      localStorage.setItem('dopapal_shop_items_v1', JSON.stringify(newUnlocked));
      setPurchaseError(null);
    } else if (userXp < cost) {
      setPurchaseError('Not enough XP to unlock this customization.');
      setTimeout(() => setPurchaseError(null), 3000);
    }
  };

  const equipTheme = (themeId) => {
    setActiveTheme(themeId);
    localStorage.setItem('dopapal_active_theme_v3', themeId);
  };

  const equipShopItem = (item) => {
    if (item.type === 'Music') {
      setActiveMusic(item.id);
      localStorage.setItem('dopapal_active_music_v1', item.id);
    } else {
      setActiveVisual(item.id);
      localStorage.setItem('dopapal_active_visual_v1', item.id);
    }
  };

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    const msg = chatInput.trim();
    setChatMessages(prev => [...prev, { sender: 'user', text: msg }]);
    setChatInput('');
    setIsTyping(true);

    setTimeout(() => {
        const aiResponses = [
            "You're doing great! Keep up the good work and maintain your streak.",
            "I suggest tackling your High Priority tasks first when your energy is highest.",
            "Remember to take short breaks if you feel overwhelmed. I can suggest a 5-minute breather task if you need it.",
            "Interesting! I'll keep that in mind to better recommend tasks for you.",
            "Let's focus on one thing at a time. What's the next most important step?"
        ];
        const randomResp = aiResponses[Math.floor(Math.random() * aiResponses.length)];
        setChatMessages(prev => [...prev, { sender: 'ai', text: randomResp }]);
        setIsTyping(false);
    }, 1500);
  };

  const fetchIntegrations = async () => {
    try {
      const statuses = await api.getIntegrationsStatus();
      setIntegrationStatuses(statuses);
    } catch (err) {
      console.error('Error fetching integrations:', err);
      setIntegrationMessage('Could not load integration status. Check that the backend is running.');
    }
  };

  useEffect(() => {
    if (tab === 'settings') {
      fetchIntegrations();
      api.getUserSettings()
        .then(data => {
          if (data?.name) {
            setUserName(data.name);
            setAccountForm(prev => ({ ...prev, name: data.name }));
          }
          if (data?.wake_time_pref) {
            const wake = data.wake_time_pref.slice(0, 5);
            setAccountForm(prev => ({ ...prev, wakeTimePref: wake }));
            localStorage.setItem('dopapal_wake_time_v1', wake);
          }
          if (data?.language) {
            setLanguageDraft(prev => ({ ...prev, primary: data.language }));
          }
        })
        .catch(() => {});
    }
  }, [tab]);

  const getIntegrationStatus = (providerId) => (
    integrationStatuses.find(status => status.provider === providerId) || { provider: providerId, connected: false }
  );

  const toggleListValue = (list, value) => (
    list.includes(value) ? list.filter(item => item !== value) : [...list, value]
  );

  const saveAccountSettings = async () => {
    setSettingsSaving(true);
    setSettingsMessage('');
    try {
      const payload = {
        name: accountForm.name.trim(),
        wake_time_pref: accountForm.wakeTimePref,
        language: languageDraft.primary,
      };
      await api.updateUserSettings(payload);
      setUserName(accountForm.name.trim() || 'Anchor User');
      localStorage.setItem('dopapal_username', accountForm.name.trim() || 'Anchor User');
      localStorage.setItem('dopapal_wake_time_v1', accountForm.wakeTimePref);
      setSettingsMessage('Account settings saved.');
    } catch (err) {
      console.error('Error saving account settings:', err);
      setSettingsMessage('Could not save account settings.');
    } finally {
      setSettingsSaving(false);
    }
  };

  const saveLanguageSettings = async () => {
    setSettingsSaving(true);
    setSettingsMessage('');
    try {
      await changeLanguage(languageDraft.primary);
      localStorage.setItem('dopapal_language_prefs_v1', JSON.stringify(languageDraft));
      setSettingsMessage('Language preferences saved.');
    } catch (err) {
      console.error('Error saving language settings:', err);
      setSettingsMessage('Could not save language preferences.');
    } finally {
      setSettingsSaving(false);
    }
  };

  const saveNotificationSettings = async () => {
    setSettingsSaving(true);
    setSettingsMessage('');
    try {
      localStorage.setItem('dopapal_notification_prefs_v1', JSON.stringify(notificationDraft));
      setSettingsMessage('Notification preferences saved.');
    } catch (err) {
      console.error('Error saving notification settings:', err);
      setSettingsMessage('Could not save notification preferences.');
    } finally {
      setSettingsSaving(false);
    }
  };

  const submitIntegration = async (e) => {
    e.preventDefault();
    const provider = INTEGRATION_PROVIDERS.find(p => p.id === selectedProvider);
    if (!provider || !integrationForm.accessToken.trim()) return;

    setIntegrationSaving(true);
    setIntegrationMessage('');
    try {
      await api.configureIntegration({
        provider: provider.id,
        accessToken: integrationForm.accessToken.trim(),
        refreshToken: integrationForm.refreshToken.trim(),
        expiresInSeconds: Number(integrationForm.expiresInSeconds) || 3600,
        settings: integrationForm.settingValue.trim()
          ? { [provider.settingKey]: integrationForm.settingValue.trim() }
          : {},
      });
      setIntegrationForm({ accessToken: '', refreshToken: '', expiresInSeconds: 3600, settingValue: '' });
      setIntegrationMessage(`${provider.name} connected.`);
      await fetchIntegrations();
    } catch (err) {
      console.error('Error saving integration:', err);
      setIntegrationMessage('Could not save integration. Check the token fields and backend logs.');
    } finally {
      setIntegrationSaving(false);
    }
  };

  const fetchTasksAndBubble = async () => {
    try {
      const data = await api.getTasks();
      const mapped = data.map(t => ({
        id: t.id,
        title: t.title,
        due: t.deadline ? new Date(t.deadline).toLocaleString() : 'No date',
        deadlineRaw: t.deadline,
        estimatedHours: t.estimated_hours ?? null,
        priority: t.pinch_score >= 80 ? 'high' : (t.pinch_score < 40 ? 'low' : 'medium'),
        done: t.status === 'completed'
      }));
      setTasks(mapped);

      const nextBubble = await api.getNextBubbleTask();
      if (nextBubble && nextBubble.primary_block) {
          setBubbleTask(nextBubble);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  };

  useEffect(() => {
    fetchTasksAndBubble();
    
    // Optional: listen for IPC reload events
    if (IS_ELECTRON && window.electronAPI.onDashboardRefresh) {
        window.electronAPI.onDashboardRefresh(() => fetchTasksAndBubble());
    }
  }, [tab]); // Refresh when tab changes

  // Auto-scroll chat
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isTyping, tab]);

  const triggerFloatingEmoji = (emoji, type = 'good', e) => {
    // try to get mouse position, otherwise default to center
    const x = e ? e.clientX : window.innerWidth / 2;
    const y = e ? e.clientY : window.innerHeight / 2;
    const id = Date.now() + Math.random();
    setFloatingEmojis(prev => [...prev, { id, emoji, type, x, y }]);
    setTimeout(() => {
        setFloatingEmojis(prev => prev.filter(f => f.id !== id));
    }, 2000);
  };

  /* ── Add Task Logic ────────────────────────────────────── */
  const submitNewTask = async (source, extraData = null) => {
    setIsSubmittingTask(true);
    try {
      if (source === 'manual') {
        let hours = 2.0;
        const dStr = taskData.duration.trim().toLowerCase();
        if (dStr === '15m' || dStr === '15 minutes') hours = 0.25;
        else if (dStr === '30m' || dStr === '30 minutes') hours = 0.5;
        else if (dStr === '45m' || dStr === '45 minutes') hours = 0.75;
        else if (dStr === '1h' || dStr === '1 hour') hours = 1.0;
        else if (dStr === '2h' || dStr === '2 hours') hours = 2.0;
        else if (dStr) {
          const match = dStr.match(/^([\d.]+)\s*(h|m|hour|min)?/);
          if (match) {
            const val = parseFloat(match[1]);
            const unit = match[2];
            if (unit && unit.startsWith('m')) hours = val / 60.0;
            else if (unit && unit.startsWith('h')) hours = val;
            else hours = val > 10 ? val / 60.0 : val;
          }
        }

        const payload = {
          title: taskData.title,
          deadline: taskData.due ? new Date(taskData.due).toISOString() : new Date(Date.now() + 86400000 * 7).toISOString(),
          estimatedHours: hours,
          sourceType: 'manual',
          interestTag: null
        };

        if (IS_ELECTRON) {
          await window.electronAPI.createTask(payload);
        } else {
          await api.createTask(payload);
        }
      } else if (source === 'ai') {
        const payload = {
          source_text: aiText,
          source_type: 'highlight'
        };

        if (IS_ELECTRON) {
          await window.electronAPI.ingestTask(payload);
        } else {
          await api.ingestTask(payload.source_text, payload.source_type);
        }
      } else if (source === 'voice' && extraData) {
        const arrayBuffer = await extraData.arrayBuffer();
        await window.electronAPI.ingestVoiceTask(arrayBuffer);
      }
      
      setTaskData({ title:'', duration:'', due:'', notes:'' });
      setAiText('');
      setShowAddTaskModal(false);
      setAddTaskView('options');
      fetchTasksAndBubble();
    } catch (e) {
      console.error("Failed to submit task:", e);
      alert("Error saving task: " + e.message);
    } finally {
      setIsSubmittingTask(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunks.current = [];
      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };
      mediaRecorder.current.start();
      setIsRecording(true);
    } catch (e) {
      console.error("Microphone error:", e);
      alert("Could not access microphone.");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder.current) return;
    mediaRecorder.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
      await submitNewTask('voice', audioBlob);
      mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
    };
    mediaRecorder.current.stop();
    setIsRecording(false);
  };

  const toggleTask = async (id, e) => {
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    const isNowDone = !task.done;
    
    setTasks(ts => ts.map(t => t.id === id ? { ...t, done: isNowDone } : t));
    
    if (isNowDone) {
        // Task Completed
        setStreak(s => {
            const ns = s + 1;
            localStorage.setItem('dopapal_streak_v3', ns);
            return ns;
        });
        setUserXp(x => {
            const nx = x + 50;
            localStorage.setItem('dopapal_xp_v3', nx);
            return nx;
        });
        const emojis = ['🚀', '🎉', '🔥', '⭐', '🤩', '🎯'];
        const em = emojis[Math.floor(Math.random() * emojis.length)];
        setStreakEmoji(em);
        setStreakAnim('bump');
        setTimeout(() => setStreakAnim(''), 300);
        triggerFloatingEmoji(em, 'good', e);

        try {
            await api.completeTask(id);
        } catch (err) {
            console.error("Failed to complete task:", err);
            setTasks(ts => ts.map(t => t.id === id ? { ...t, done: false } : t));
        }
    } else {
        // Task Missed / Un-checked
        setStreak(s => {
            const ns = Math.max(0, s - 1);
            localStorage.setItem('dopapal_streak_v3', ns);
            return ns;
        });
        const sadEmojis = ['🧊', '🥶', '🥺', '🌧️', '📉'];
        const em = sadEmojis[Math.floor(Math.random() * sadEmojis.length)];
        setStreakEmoji(em);
        setStreakAnim('shake');
        setTimeout(() => setStreakAnim(''), 400);
        triggerFloatingEmoji(em, 'bad', e);
        // Note: Demo uncheck logic mocked.
    }
  };

  const deleteTask = async (id) => {
    setTasks(ts => ts.filter(t => t.id !== id));
    try {
        await api.deleteTask(id);
        fetchTasksAndBubble();
    } catch (e) {
        console.error("Failed to delete task:", e);
        fetchTasksAndBubble();
    }
  };

  const updateTaskDetails = async (id, updates) => {
    let payload = {};
    if (updates.title !== undefined) payload.title = updates.title;
    if (updates.deadline !== undefined) payload.deadline = updates.deadline;
    if (updates.estimatedHours !== undefined) payload.estimated_hours = updates.estimatedHours;
    if (updates.priority !== undefined) {
      if (updates.priority === 'high') payload.pinch_score = 90.0;
      else if (updates.priority === 'low') payload.pinch_score = 20.0;
      else payload.pinch_score = 50.0;
    }

    // Optimistic update for local state
    setTasks(ts => ts.map(t => t.id === id ? {
      ...t,
      ...updates,
      due: updates.deadline ? new Date(updates.deadline).toLocaleString() : t.due,
      deadlineRaw: updates.deadline ?? t.deadlineRaw,
      estimatedHours: updates.estimatedHours ?? t.estimatedHours,
    } : t));

    try {
      await api.updateTask(id, payload);
      fetchTasksAndBubble();
    } catch (e) {
      console.error("Failed to update task:", e);
      fetchTasksAndBubble();
    }
  };

  const pending = tasks.filter(t => !t.done);
  const done    = tasks.filter(t =>  t.done);

  const close = () => {
    if (IS_ELECTRON) window.electronAPI.closeDashboard();
    else             window.history.back();
  };

  const maximize = () => {
    if (IS_ELECTRON) window.electronAPI.maximizeDashboard();
  };

  const minimize = () => {
    if (IS_ELECTRON) window.electronAPI.minimizeDashboard();
  };

  return (
    <div className="d-root">

      {/* ── Title bar (draggable, frameless) ────────────── */}
      <div className="d-titlebar">
        <div className="d-titlebar-drag">
          <div className="d-logo">🧠</div>
          <span className="d-appname">DopaPal</span>
        </div>
        <div className="d-titlebar-actions">
          <button className="d-titlebar-btn" onClick={minimize}><IconMinus /></button>
          <button className="d-titlebar-btn" onClick={maximize}><IconMaximize /></button>
          <button className="d-titlebar-close" onClick={close}><IconClose /></button>
        </div>
      </div>

      {/* ── Sidebar ─────────────────────────────────────── */}
      <div className="d-layout">
        <aside className="d-sidebar">
          <div className="d-sidebar-main">
            {[
              { id: 'home',      label: t('dashboard.home'),     Icon: IconHome },
              { id: 'tasks',     label: t('dashboard.allTasks'), Icon: IconTask },
              { id: 'assistant', label: 'Assistant',             Icon: IconSparkle },
            ].map(({ id, label, Icon }) => (
              <button
                key={id}
                className={`d-nav-btn${tab === id ? ' active' : ''}`}
                onClick={() => setTab(id)}
              >
                <Icon />
                <span>{label}</span>
              </button>
            ))}
          </div>

          <div className="d-sidebar-tools">
            <button
              className={`d-profile-nav${tab === 'profile' ? ' active' : ''}`}
              onClick={() => {
                setTab('profile');
              }}
              title="Profile"
              aria-label="Profile"
            >
              <span className="d-profile-nav-avatar">{USER.avatar}</span>
            </button>
            <button
              className={`d-icon-nav${tab === 'shop' ? ' active' : ''}`}
              onClick={() => setTab('shop')}
              title="Shop"
              aria-label="Shop"
            >
              <IconShop />
            </button>
            <button
              className={`d-icon-nav${tab === 'settings' ? ' active' : ''}`}
              onClick={() => setTab('settings')}
              title={t('dashboard.settings')}
              aria-label={t('dashboard.settings')}
            >
              <IconSettings />
            </button>
          </div>
        </aside>

        {/* ── Main content ──────────────────────────────── */}
        <main className="d-main">

          {/* ══ HOME TAB ══ */}
          {tab === 'home' && (
            <div className="d-section fade-in">
              {/* Greeting */}
              <div className="d-greeting">
                <div>
                  <h1 className="d-h1">{t('dashboard.goodEvening')}, {userName.split(' ')[0]} 👋</h1>
                  <p className="d-sub">{t('dashboard.letsCrush')}</p>
                </div>
                <div className={`d-streak ${streakAnim}`}>
                  <span style={{ fontSize: '18px' }}>{streakEmoji}</span> <span>{streak} {t('dashboard.dayStreak')}</span>
                </div>
              </div>

              {/* AI Recommend card */}
              {bubbleTask && bubbleTask.primary_block ? (
              <div className="d-card d-card--ai">
                <div className="d-card-header">
                  <IconSparkle />
                  <span>AI Recommendation</span>
                  <span className="d-chip">Now</span>
                </div>
                <h2 className="d-card-title">{bubbleTask.primary_block.task_title}</h2>
                <p className="d-card-reason">Based on your cognitive state ({bubbleTask.state_score}), this is the best task to tackle.</p>
                <div className="d-card-meta">
                  <span>⚡ {bubbleTask.mode === 'focused' ? 'High' : 'Low'} energy</span>
                  <span>⏱ {bubbleTask.primary_block.duration_minutes} min</span>
                </div>
                <button className="d-btn d-btn--primary" onClick={async () => {
                  await api.completeSubBlock(bubbleTask.primary_block.sub_block_id);
                  fetchTasksAndBubble();
                }}>Complete Block →</button>
              </div>
              ) : (
                <div className="d-card d-card--ai" style={{ alignItems: 'center', textAlign: 'center', padding: '40px 20px' }}>
                  <div style={{ animation: 'pulse 2s infinite', color: 'var(--accent)', marginBottom: '12px' }}>
                    <IconSparkle size={48} />
                  </div>
                  <h2 className="d-card-title" style={{ fontSize: '24px', marginBottom: '8px' }}>All Caught Up! ✨</h2>
                  <p className="d-card-reason" style={{ fontSize: '14px', opacity: 0.8 }}>You have conquered all your tasks. Take a breath and enjoy the dopamine.</p>
                </div>
              )}

              {/* Today's tasks */}
              <div className="d-card">
                <div className="d-card-header">
                  <IconTask />
                  <span>{t('dashboard.allTasks')}</span>
                  <span className="d-chip">{pending.filter(t => t.due === 'Today').length} {t('dashboard.upNext')}</span>
                </div>
                <div className="d-task-list">
                  {tasks.filter(t => t.due === 'Today').map(t => (
                    <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={deleteTask} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ══ TASKS TAB ══ */}
          {tab === 'tasks' && (
            <div className="d-section fade-in">
              <div className="d-section-header">
                <h1 className="d-h1">All Tasks</h1>
                <button className="d-btn d-btn--primary" style={{ gap: 6 }} onClick={() => {
                  setShowAddTaskModal(true);
                  setAddTaskView('options');
                }}>
                  <IconPlus /> Add Task
                </button>
              </div>

              {pending.length > 0 && (
                <div className="d-card">
                  <div className="d-card-header"><span>Pending</span><span className="d-chip">{pending.length}</span></div>
                  <div className="d-task-list">
                    {pending.map(t => <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={deleteTask} onUpdateTask={updateTaskDetails} />)}
                  </div>
                </div>
              )}

              {done.length > 0 && (
                <div className="d-card" style={{ opacity: .7 }}>
                  <div className="d-card-header"><span>Completed</span><span className="d-chip">{done.length}</span></div>
                  <div className="d-task-list">
                    {done.map(t => <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={deleteTask} onUpdateTask={updateTaskDetails} />)}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ══ ACCOUNT TAB ══ */}
          {tab === 'profile' && (
            <div className="d-section fade-in">
              <div className="d-card">
                <div className="d-card-header"><IconUser /><span>Profile</span></div>
                <p className="d-field-help">This is your personal summary page. Use Account in Settings to edit the profile details that appear here.</p>

                <div className="d-profile-hero">
                  <div className="d-profile-hero-avatar">{USER.avatar}</div>
                  <div className="d-profile-hero-copy">
                    <h2 className="d-card-title">{userName}</h2>
                    <p className="d-card-reason">{USER.email}</p>
                    <div className="d-profile-tags">
                      <span className="d-badge d-badge--accent">{USER.level}</span>
                      <span className="d-badge">Language: {languageDraft.primary.toUpperCase()}</span>
                      <span className="d-badge">Theme: {activeTheme}</span>
                    </div>
                  </div>
                </div>

                <div className="d-profile-stats">
                  <div className="d-profile-stat">
                    <span className="d-field-label">Day streak</span>
                    <strong>{streak}</strong>
                    <p className="d-field-help">Consecutive days with completed progress.</p>
                  </div>
                  <div className="d-profile-stat">
                    <span className="d-field-label">XP</span>
                    <strong>{userXp}</strong>
                    <p className="d-field-help">Your accumulated progress currency for themes and customization.</p>
                  </div>
                  <div className="d-profile-stat">
                    <span className="d-field-label">Completed tasks</span>
                    <strong>{done.length}</strong>
                    <p className="d-field-help">Tasks you have already finished and archived.</p>
                  </div>
                  <div className="d-profile-stat">
                    <span className="d-field-label">Remaining tasks</span>
                    <strong>{pending.length}</strong>
                    <p className="d-field-help">Tasks still waiting for your attention.</p>
                  </div>
                  <div className="d-profile-stat">
                    <span className="d-field-label">Themes unlocked</span>
                    <strong>{unlockedThemes.length}</strong>
                    <p className="d-field-help">How many visual themes you have already earned.</p>
                  </div>
                  <div className="d-profile-stat">
                    <span className="d-field-label">Sync connections</span>
                    <strong>{integrationStatuses.filter(status => status.connected).length}</strong>
                    <p className="d-field-help">Connected services currently available for sync.</p>
                  </div>
                </div>

                <div className="d-settings-grid">
                  <div>
                    <span className="d-field-label">Active music</span>
                    <p className="d-field-help">The currently selected background sound profile, or none if nothing is active.</p>
                    <div className="d-integration-summary">
                      <div><span className="d-integration-label">Music</span><strong>{activeMusic}</strong></div>
                    </div>
                  </div>
                  <div>
                    <span className="d-field-label">Active visual</span>
                    <p className="d-field-help">The visual customization currently applied to the app shell.</p>
                    <div className="d-integration-summary">
                      <div><span className="d-integration-label">Visual</span><strong>{activeVisual}</strong></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === 'account' && (
            <div className="d-section fade-in">
              <h1 className="d-h1">Account</h1>

              {/* Profile card */}
              <div className="d-card d-profile-card">
                <div className="d-avatar">{USER.avatar}</div>
                <div className="d-profile-info">
                  {isEditingName ? (
                    <input 
                      type="text" 
                      value={userName} 
                      onChange={(e) => setUserName(e.target.value)} 
                      onBlur={() => { setIsEditingName(false); localStorage.setItem('dopapal_username', userName); }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { setIsEditingName(false); localStorage.setItem('dopapal_username', userName); } }}
                      autoFocus
                      style={{ background: 'transparent', border: 'none', borderBottom: '1px solid var(--accent)', color: 'white', fontSize: '20px', fontWeight: 'bold', outline: 'none', width: '100%', marginBottom: '4px' }}
                    />
                  ) : (
                    <h2 className="d-profile-name" onClick={() => setIsEditingName(true)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }} title="Click to edit">
                      {userName} <span style={{ fontSize: '12px', opacity: 0.5 }}>✎</span>
                    </h2>
                  )}
                  <p className="d-profile-email">{USER.email}</p>
                  <span className="d-badge d-badge--accent">{USER.level}</span>
                </div>
              </div>

              {/* XP bar */}
              <div className="d-card">
                <div className="d-card-header"><IconSparkle /><span>Progress</span></div>
                <div className="d-xp-row">
                  <span className="d-xp-label">XP</span>
                  <div className="d-xp-bar">
                    <div className="d-xp-fill" style={{ width: `${Math.min(100, (userXp / 5000) * 100)}%` }} />
                  </div>
                  <span className="d-xp-label">{userXp}/5000</span>
                </div>
                <div className="d-stats-row">
                  <div className="d-stat">
                    <span className="d-stat-val">{streak}</span>
                    <span className="d-stat-lbl">Day Streak</span>
                  </div>
                  <div className="d-stat">
                    <span className="d-stat-val">{done.length}</span>
                    <span className="d-stat-lbl">Completed</span>
                  </div>
                  <div className="d-stat">
                    <span className="d-stat-val">{pending.length}</span>
                    <span className="d-stat-lbl">Remaining</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ══ SETTINGS TAB ══ */}
          {tab === 'settings' && (
            <div className="d-section fade-in">
              <div className="d-greeting" style={{ alignItems: 'center' }}>
                <div>
                  <h1 className="d-h1">Settings</h1>
                  <p className="d-sub">Pick a section, then adjust only the settings for that area.</p>
                </div>
                {settingsMessage && <span className="d-badge d-badge--accent">{settingsMessage}</span>}
              </div>

              <div className="d-settings-shell">
                <aside className="d-settings-nav">
                  {[
                    { id: 'account', title: 'Account', desc: 'Name, wake time, and profile details.' },
                    { id: 'language', title: 'Language', desc: 'Locale, formatting, and text behavior.' },
                    { id: 'notifications', title: 'Notifications', desc: 'Delivery, intensity, and quiet hours.' },
                    { id: 'sync', title: 'Sync', desc: 'Connected services and provider settings.' },
                    { id: 'privacy', title: 'Privacy', desc: 'Storage and data-sharing preferences.' },
                  ].map(section => (
                    <button
                      key={section.id}
                      className={`d-settings-nav-item${settingsSection === section.id ? ' active' : ''}`}
                      onClick={() => setSettingsSection(section.id)}
                    >
                      <strong>{section.title}</strong>
                      <span>{section.desc}</span>
                    </button>
                  ))}
                </aside>

                <div className="d-settings-panel">
                  {settingsSection === 'account' && (
                    <div className="d-card">
                      <div className="d-card-header"><IconUser /><span>Account</span></div>
                      <p className="d-field-help">This controls your display name in the app and the wake-up time used for scheduling and prompts.</p>
                      <div className="d-settings-grid">
                        <label>
                          <span className="d-field-label">Display name</span>
                          <p className="d-field-help">Shown in the sidebar greeting, profile area, and task ownership.</p>
                          <input className="d-input" value={accountForm.name} onChange={e => setAccountForm({ ...accountForm, name: e.target.value })} placeholder="Display name" />
                        </label>
                        <label>
                          <span className="d-field-label">Wake time</span>
                          <p className="d-field-help">The time the assistant should treat as your usual morning start.</p>
                          <input className="d-input" type="time" value={accountForm.wakeTimePref} onChange={e => setAccountForm({ ...accountForm, wakeTimePref: e.target.value })} />
                        </label>
                      </div>
                      <div className="d-integration-summary">
                        <div><span className="d-integration-label">Primary account</span><strong>{USER.email}</strong></div>
                        <div><span className="d-integration-label">Wake time</span><strong>{accountForm.wakeTimePref || '07:30'}</strong></div>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="d-btn d-btn--primary" onClick={saveAccountSettings} disabled={settingsSaving}>{settingsSaving ? 'Saving...' : 'Save Account'}</button>
                      </div>
                    </div>
                  )}

                  {settingsSection === 'language' && (
                    <div className="d-card">
                      <div className="d-card-header"><span>🌐</span><span>{t('dashboard.language')}</span></div>
                      <p className="d-field-help">Choose how the interface reads, formats dates and numbers, and handles mixed-language content.</p>
                      <div className="d-field-block">
                        <span className="d-field-label">Primary language</span>
                        <p className="d-field-help">This is the app language used for menus, labels, and helper text.</p>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(128px, 1fr))', gap: 10 }}>
                          {LANGUAGE_OPTIONS.map(option => (
                            <button
                              key={option.code}
                              className="d-btn d-btn--secondary"
                              onClick={() => {
                                setLanguageDraft(prev => ({ ...prev, primary: option.code }));
                                changeLanguage(option.code);
                              }}
                              style={{
                                justifyContent: 'flex-start',
                                padding: '12px',
                                borderColor: languageDraft.primary === option.code ? 'var(--accent)' : 'rgba(255,255,255,0.12)',
                                background: languageDraft.primary === option.code ? 'var(--accent-dim)' : 'rgba(255,255,255,0.03)',
                                color: languageDraft.primary === option.code ? 'var(--accent)' : 'var(--text)',
                                flexDirection: 'column',
                                alignItems: 'flex-start',
                                gap: '4px',
                              }}
                            >
                              <strong>{option.native}</strong>
                              <span style={{ fontSize: 12, color: 'inherit', opacity: 0.8 }}>{option.label}</span>
                              <span style={{ fontSize: 11, opacity: 0.7 }}>{option.region}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="d-settings-grid">
                        <label>
                          <span className="d-field-label">Secondary language</span>
                          <p className="d-field-help">Use this as the fallback language for bilingual prompts and overlays.</p>
                          <select className="d-input" value={languageDraft.secondary} onChange={e => setLanguageDraft({ ...languageDraft, secondary: e.target.value })}>
                            {LANGUAGE_OPTIONS.filter(option => option.code !== languageDraft.primary).map(option => <option key={option.code} value={option.code}>{option.label}</option>)}
                          </select>
                        </label>
                        <label>
                          <span className="d-field-label">Content mode</span>
                          <p className="d-field-help">Controls whether the app keeps one language, blends two, or auto-detects content.</p>
                          <select className="d-input" value={languageDraft.contentMode} onChange={e => setLanguageDraft({ ...languageDraft, contentMode: e.target.value })}>
                            <option value="auto">Auto detect content</option>
                            <option value="primary">Primary language only</option>
                            <option value="bilingual">Bilingual mode</option>
                          </select>
                        </label>
                        <label>
                          <span className="d-field-label">Date format</span>
                          <p className="d-field-help">Affects how deadlines and reminders are displayed everywhere in the app.</p>
                          <select className="d-input" value={languageDraft.dateFormat} onChange={e => setLanguageDraft({ ...languageDraft, dateFormat: e.target.value })}>
                            <option value="locale">Locale dates</option>
                            <option value="iso">ISO dates</option>
                          </select>
                        </label>
                        <label>
                          <span className="d-field-label">Number format</span>
                          <p className="d-field-help">Controls whether values are shown plainly or in compact human-friendly form.</p>
                          <select className="d-input" value={languageDraft.numberFormat} onChange={e => setLanguageDraft({ ...languageDraft, numberFormat: e.target.value })}>
                            <option value="locale">Locale numbers</option>
                            <option value="compact">Compact numbers</option>
                            <option value="plain">Plain numbers</option>
                          </select>
                        </label>
                      </div>
                      <label className="d-toggle-row"><span>Transliterate borrowed content</span><input type="checkbox" checked={languageDraft.transliteration} onChange={e => setLanguageDraft({ ...languageDraft, transliteration: e.target.checked })} /></label>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="d-btn d-btn--primary" onClick={saveLanguageSettings} disabled={settingsSaving}>{settingsSaving ? 'Saving...' : 'Save Language'}</button>
                      </div>
                    </div>
                  )}

                  {settingsSection === 'notifications' && (
                    <div className="d-card">
                      <div className="d-card-header"><span>Notifications</span></div>
                      <p className="d-field-help">Choose how intense alerts should be, which channels they use, and what kinds of events they should cover.</p>
                      <div className="d-field-block">
                        <span className="d-field-label">Notification level</span>
                        <p className="d-field-help">Higher levels surface more nudges and summaries; lower levels keep the app quieter.</p>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 10 }}>
                          {NOTIFICATION_LEVELS.map(level => (
                            <button
                              key={level.id}
                              className="d-btn d-btn--secondary"
                              onClick={() => setNotificationDraft({ ...notificationDraft, level: level.id })}
                              style={{
                                justifyContent: 'flex-start',
                                padding: '12px',
                                borderColor: notificationDraft.level === level.id ? 'var(--accent)' : 'rgba(255,255,255,0.12)',
                                background: notificationDraft.level === level.id ? 'var(--accent-dim)' : 'rgba(255,255,255,0.03)',
                                color: notificationDraft.level === level.id ? 'var(--accent)' : 'var(--text)',
                                flexDirection: 'column',
                                alignItems: 'flex-start',
                                gap: '4px',
                              }}
                            >
                              <strong>{level.label}</strong>
                              <span style={{ fontSize: 12, opacity: 0.8 }}>{level.detail}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="d-field-block">
                        <span className="d-field-label">Delivery channels</span>
                        <p className="d-field-help">Pick where alerts are allowed to show up.</p>
                        <div className="d-settings-pills">
                          {NOTIFICATION_CHANNELS.map(channel => (
                            <button key={channel.id} className={`d-pill${notificationDraft.channels.includes(channel.id) ? ' active' : ''}`} onClick={() => setNotificationDraft({ ...notificationDraft, channels: toggleListValue(notificationDraft.channels, channel.id) })}>{channel.label}</button>
                          ))}
                        </div>
                      </div>
                      <div className="d-field-block">
                        <span className="d-field-label">Categories</span>
                        <p className="d-field-help">Decide which event types should trigger notifications.</p>
                        <div className="d-settings-pills">
                          {NOTIFICATION_CATEGORIES.map(category => (
                            <button key={category.id} className={`d-pill${notificationDraft.categories.includes(category.id) ? ' active' : ''}`} onClick={() => setNotificationDraft({ ...notificationDraft, categories: toggleListValue(notificationDraft.categories, category.id) })}>{category.label}</button>
                          ))}
                        </div>
                      </div>
                      <div className="d-settings-grid">
                        <label>
                          <span className="d-field-label">Digest cadence</span>
                          <p className="d-field-help">How often the app should bundle summary notifications.</p>
                          <select className="d-input" value={notificationDraft.digest} onChange={e => setNotificationDraft({ ...notificationDraft, digest: e.target.value })}>
                            {NOTIFICATION_DIGESTS.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
                          </select>
                        </label>
                        <label>
                          <span className="d-field-label">Sound profile</span>
                          <p className="d-field-help">Controls the style of sound cues when notifications are enabled.</p>
                          <select className="d-input" value={notificationDraft.soundProfile} onChange={e => setNotificationDraft({ ...notificationDraft, soundProfile: e.target.value })}>
                            <option value="soft">Soft</option>
                            <option value="balanced">Balanced</option>
                            <option value="sharp">Sharp</option>
                            <option value="silent">Silent</option>
                          </select>
                        </label>
                        <label>
                          <span className="d-field-label">Quiet hours start</span>
                          <p className="d-field-help">Alerts are muted or reduced after this time.</p>
                          <input className="d-input" type="time" value={notificationDraft.quietStart} onChange={e => setNotificationDraft({ ...notificationDraft, quietStart: e.target.value })} />
                        </label>
                        <label>
                          <span className="d-field-label">Quiet hours end</span>
                          <p className="d-field-help">Notifications resume after this time.</p>
                          <input className="d-input" type="time" value={notificationDraft.quietEnd} onChange={e => setNotificationDraft({ ...notificationDraft, quietEnd: e.target.value })} />
                        </label>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="d-btn d-btn--primary" onClick={saveNotificationSettings} disabled={settingsSaving}>{settingsSaving ? 'Saving...' : 'Save Notifications'}</button>
                      </div>
                    </div>
                  )}

                  {settingsSection === 'sync' && (
                    <div className="d-card">
                      <div className="d-card-header"><IconSync /><span>Sync</span></div>
                      <p className="d-field-help">Each provider can be connected separately, and each connection carries its own token and provider-specific metadata.</p>
                      <div className="d-integrations-layout" style={{ padding: 0, gridTemplateColumns: 'minmax(220px, 280px) 1fr' }}>
                        <div className="d-card d-integrations-list" style={{ padding: 16 }}>
                          {INTEGRATION_PROVIDERS.map(provider => {
                            const status = getIntegrationStatus(provider.id);
                            return (
                              <button key={provider.id} className={`d-integration-provider${selectedProvider === provider.id ? ' active' : ''}`} onClick={() => { setSelectedProvider(provider.id); setIntegrationMessage(''); }}>
                                <span className="d-integration-dot" style={{ background: status.connected ? '#34d399' : 'rgba(255,255,255,0.25)' }} />
                                <span>{provider.name}</span>
                                <span className={`d-integration-status ${status.connected ? 'connected' : ''}`}>{status.connected ? (status.is_expired ? 'Expired' : 'Connected') : 'Off'}</span>
                              </button>
                            );
                          })}
                        </div>
                        <div className="d-card d-integrations-detail" style={{ padding: 18 }}>
                          {(() => {
                            const provider = INTEGRATION_PROVIDERS.find(p => p.id === selectedProvider) || INTEGRATION_PROVIDERS[0];
                            const status = getIntegrationStatus(provider.id);
                            const expiresAt = status.expires_at ? new Date(status.expires_at).toLocaleString() : 'Not connected';
                            return (
                              <>
                                <div className="d-card-header">
                                  <IconLink />
                                  <span>{provider.name}</span>
                                  <span className={`d-chip ${status.connected ? '' : 'd-chip--muted'}`}>{status.connected ? (status.is_expired ? 'Expired' : 'Connected') : 'Disconnected'}</span>
                                </div>
                                <div className="d-integration-summary">
                                  <div><span className="d-integration-label">Expires</span><strong>{expiresAt}</strong></div>
                                  <div><span className="d-integration-label">{provider.settingLabel}</span><strong>{status.settings?.[provider.settingKey] || 'None'}</strong></div>
                                </div>
                                <form className="d-modal-form" onSubmit={submitIntegration}>
                                  <p className="d-field-help">Access token or API key used to authenticate this provider.</p>
                                  <input className="d-input" type="password" placeholder={provider.tokenLabel} value={integrationForm.accessToken} onChange={e => setIntegrationForm({ ...integrationForm, accessToken: e.target.value })} />
                                  <p className="d-field-help">Optional refresh token for OAuth-style connections.</p>
                                  <input className="d-input" type="password" placeholder="Refresh token (optional)" value={integrationForm.refreshToken} onChange={e => setIntegrationForm({ ...integrationForm, refreshToken: e.target.value })} />
                                  <div className="d-integration-form-grid">
                                    <label>
                                      <span className="d-field-label">{provider.settingLabel}</span>
                                      <p className="d-field-help">Provider-specific metadata such as a course, database, or project reference.</p>
                                      <input className="d-input" placeholder={provider.settingLabel} value={integrationForm.settingValue} onChange={e => setIntegrationForm({ ...integrationForm, settingValue: e.target.value })} />
                                    </label>
                                    <label>
                                      <span className="d-field-label">Expires in seconds</span>
                                      <p className="d-field-help">How long this token should be considered valid before expiring.</p>
                                      <input className="d-input" type="number" min="60" step="60" value={integrationForm.expiresInSeconds} onChange={e => setIntegrationForm({ ...integrationForm, expiresInSeconds: e.target.value })} />
                                    </label>
                                  </div>
                                  <button className="d-btn d-btn--primary" disabled={integrationSaving || !integrationForm.accessToken.trim()} style={{ alignSelf: 'stretch' }}>{integrationSaving ? 'Saving...' : `Connect ${provider.name}`}</button>
                                </form>
                                {integrationMessage && <div className="d-integration-message">{integrationMessage}</div>}
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                  )}

                  {settingsSection === 'privacy' && (
                    <div className="d-card">
                      <div className="d-card-header"><span>Privacy</span></div>
                      <p className="d-field-help">These controls decide what the app stores locally and what kinds of usage data can leave the device.</p>
                      <div className="d-settings-grid">
                        <label className="d-toggle-row"><span>Share anonymous usage data</span><input type="checkbox" /></label>
                        <label className="d-toggle-row"><span>Store task history locally</span><input type="checkbox" defaultChecked /></label>
                        <label className="d-toggle-row"><span>Encrypt local sync cache</span><input type="checkbox" defaultChecked /></label>
                        <label className="d-toggle-row"><span>Allow crash diagnostics</span><input type="checkbox" defaultChecked /></label>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          {tab === 'settings' && false && (
            <div className="d-section fade-in">
              <h1 className="d-h1">Settings</h1>
              
              {/* Language Selector */}
              <div className="d-card" style={{ marginBottom: 16 }}>
                <div className="d-card-header"><span>🌐</span><span>{t('dashboard.language')}</span></div>
                <div style={{ display: 'flex', gap: 10, padding: '12px 0 0 0' }}>
                  {[{code:'ar', label:'العربية 🇸🇦'}, {code:'en', label:'English 🇬🇧'}].map(({ code, label }) => (
                    <button
                      key={code}
                      onClick={() => changeLanguage(code)}
                      style={{
                        flex: 1, padding: '10px', borderRadius: '10px', cursor: 'pointer',
                        border: lang === code ? '2px solid var(--accent)' : '1px solid rgba(255,255,255,0.1)',
                        background: lang === code ? 'var(--accent-dim)' : 'transparent',
                        color: lang === code ? 'var(--accent)' : 'rgba(255,255,255,0.7)',
                        fontWeight: lang === code ? 700 : 400,
                        fontSize: '14px', transition: 'all 0.2s'
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="d-card">
                <div className="d-card-header"><span>App Settings</span></div>
                <div className="d-settings-list">
                  {['Notifications', 'Privacy'].map(s => (
                    <div 
                      key={s} 
                      className="d-setting-row" 
                      style={{ display: 'flex', justifyContent: 'space-between' }}
                    >
                      <span>{s}</span>
                      {s === 'Notifications' ? (
                        <div style={{ width: 36, height: 20, background: '#8b5cf6', borderRadius: 10, position: 'relative' }}>
                          <div style={{ position: 'absolute', right: 2, top: 2, width: 16, height: 16, background: 'white', borderRadius: '50%' }}></div>
                        </div>
                      ) : (
                        <span className="d-setting-arrow">›</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'assistant' && (
            <div className="d-section fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '10px 0' }}>
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '0' }}>
                <h1 className="d-h1" style={{ margin: 0, fontSize: '18px' }}>DopaPal Assistant</h1>
              </div>
              
              <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {chatMessages.map((m, i) => (
                  <div key={i} style={{ 
                      alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start', 
                      background: m.sender === 'user' ? '#8b5cf6' : 'rgba(255,255,255,0.05)', 
                      color: 'white', padding: '12px 16px', borderRadius: '16px', 
                      borderBottomRightRadius: m.sender === 'user' ? '4px' : '16px', 
                      borderBottomLeftRadius: m.sender === 'ai' ? '4px' : '16px', 
                      maxWidth: '80%', lineHeight: '1.4' 
                  }}>
                    {m.text}
                  </div>
                ))}
                {isTyping && (
                  <div style={{ alignSelf: 'flex-start', background: 'rgba(255,255,255,0.05)', color: '#9ca3af', padding: '12px 16px', borderRadius: '16px', borderBottomLeftRadius: '4px' }}>
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '20px' }}>
                       <span style={{ width: '6px', height: '6px', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.5s infinite' }}></span>
                       <span style={{ width: '6px', height: '6px', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.2s' }}></span>
                       <span style={{ width: '6px', height: '6px', background: '#9ca3af', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.4s' }}></span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div style={{ display: 'flex', gap: '8px', padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <input 
                  type="text" 
                  value={chatInput} 
                  onChange={e => setChatInput(e.target.value)} 
                  onKeyDown={e => e.key === 'Enter' && handleSendChat()}
                  placeholder="Message DopaPal AI..." 
                  style={{ flex: 1, background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '12px 16px', color: 'white', outline: 'none', fontSize: '14px' }} 
                />
                <button className="d-btn d-btn--primary" onClick={handleSendChat} style={{ borderRadius: '12px', padding: '0 20px' }}>Send</button>
              </div>
            </div>
          )}

          {tab === 'sync' && (
            <div className="d-section fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '10px 0' }}>
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '0' }}>
                <h1 className="d-h1" style={{ margin: 0, fontSize: '18px' }}>Sync</h1>
                <span className="d-badge d-badge--accent">
                  {integrationStatuses.filter(status => status.connected).length}/{INTEGRATION_PROVIDERS.length} connected
                </span>
              </div>

              <div className="d-integrations-layout">
                <div className="d-card d-integrations-list">
                  <div className="d-card-header"><IconLink /><span>Providers</span></div>
                  {INTEGRATION_PROVIDERS.map(provider => {
                    const status = getIntegrationStatus(provider.id);
                    return (
                      <button
                        key={provider.id}
                        className={`d-integration-provider${selectedProvider === provider.id ? ' active' : ''}`}
                        onClick={() => {
                          setSelectedProvider(provider.id);
                          setIntegrationMessage('');
                        }}
                      >
                        <span className="d-integration-dot" style={{ background: status.connected ? '#34d399' : 'rgba(255,255,255,0.25)' }} />
                        <span>{provider.name}</span>
                        <span className={`d-integration-status ${status.connected ? 'connected' : ''}`}>
                          {status.connected ? (status.is_expired ? 'Expired' : 'Connected') : 'Off'}
                        </span>
                      </button>
                    );
                  })}
                </div>

                <div className="d-card d-integrations-detail">
                  {(() => {
                    const provider = INTEGRATION_PROVIDERS.find(p => p.id === selectedProvider) || INTEGRATION_PROVIDERS[0];
                    const status = getIntegrationStatus(provider.id);
                    const expiresAt = status.expires_at ? new Date(status.expires_at).toLocaleString() : 'Not connected';
                    return (
                      <>
                        <div className="d-card-header">
                          <IconLink />
                          <span>{provider.name}</span>
                          <span className={`d-chip ${status.connected ? '' : 'd-chip--muted'}`}>
                            {status.connected ? (status.is_expired ? 'Expired' : 'Connected') : 'Disconnected'}
                          </span>
                        </div>

                        <div className="d-integration-summary">
                          <div>
                            <span className="d-integration-label">Expires</span>
                            <strong>{expiresAt}</strong>
                          </div>
                          <div>
                            <span className="d-integration-label">{provider.settingLabel}</span>
                            <strong>{status.settings?.[provider.settingKey] || 'None'}</strong>
                          </div>
                        </div>

                        <form className="d-modal-form" onSubmit={submitIntegration}>
                          <input
                            className="d-input"
                            type="password"
                            placeholder={provider.tokenLabel}
                            value={integrationForm.accessToken}
                            onChange={e => setIntegrationForm({ ...integrationForm, accessToken: e.target.value })}
                          />
                          <input
                            className="d-input"
                            type="password"
                            placeholder="Refresh token (optional)"
                            value={integrationForm.refreshToken}
                            onChange={e => setIntegrationForm({ ...integrationForm, refreshToken: e.target.value })}
                          />
                          <div className="d-integration-form-grid">
                            <input
                              className="d-input"
                              placeholder={provider.settingLabel}
                              value={integrationForm.settingValue}
                              onChange={e => setIntegrationForm({ ...integrationForm, settingValue: e.target.value })}
                            />
                            <input
                              className="d-input"
                              type="number"
                              min="60"
                              step="60"
                              value={integrationForm.expiresInSeconds}
                              onChange={e => setIntegrationForm({ ...integrationForm, expiresInSeconds: e.target.value })}
                              title="Token lifetime in seconds"
                            />
                          </div>
                          <button className="d-btn d-btn--primary" disabled={integrationSaving || !integrationForm.accessToken.trim()} style={{ alignSelf: 'stretch' }}>
                            {integrationSaving ? 'Saving...' : `Connect ${provider.name}`}
                          </button>
                        </form>

                        {integrationMessage && (
                          <div className="d-integration-message">{integrationMessage}</div>
                        )}
                      </>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}

          {tab === 'shop' && (
            <div className="d-section fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '10px 0' }}>
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <h1 className="d-h1" style={{ margin: 0, fontSize: '18px' }}>Shop</h1>
                  <div className="d-streak" style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)', padding: '4px 12px', borderRadius: '16px' }}>
                    <IconSparkle /> <span style={{ fontWeight: 600 }}>{userXp} XP</span>
                  </div>
                </div>
              </div>

              {purchaseError && (
                 <div style={{ margin: '16px 24px 0 24px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', borderRadius: '8px', textAlign: 'center', fontSize: '14px', fontWeight: 500 }}>
                    {purchaseError}
                 </div>
              )}
              
              <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {THEMES.map(t => {
                  const isUnlocked = unlockedThemes.includes(t.id);
                  const isActive = activeTheme === t.id;
                  return (
                    <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'var(--surface2)', borderRadius: '12px', border: isActive ? `2px solid ${t.accent}` : '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: `linear-gradient(135deg, ${t.accent}, ${t.dim})`, border: '2px solid rgba(255,255,255,0.1)' }}></div>
                        <div>
                          <div style={{ fontSize: '16px', fontWeight: 600, color: 'white' }}>{t.name}</div>
                          {!isUnlocked && (
                              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24', padding: '4px 8px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, marginTop: '6px' }}>
                                <IconSparkle size={12} /> {t.cost} XP
                              </div>
                          )}
                          {isUnlocked && <div style={{ fontSize: '13px', color: '#34d399', marginTop: '6px', fontWeight: 500 }}>✓ Unlocked</div>}
                        </div>
                      </div>
                      <div>
                        {isActive ? (
                          <button className="d-btn d-btn--secondary" disabled style={{ background: 'transparent', border: `1px solid ${t.accent}`, color: t.accent }}>Equipped</button>
                        ) : isUnlocked ? (
                          <button className="d-btn" onClick={() => equipTheme(t.id)} style={{ background: t.accent }}>Equip</button>
                        ) : (
                          <button className="d-btn" onClick={() => buyTheme(t.id, t.cost)} style={{ background: '#fbbf24', color: 'black' }}>
                            Buy Theme
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}

                <div className="d-shop-section-title">
                  <IconMusic />
                  <span>Music & Visuals</span>
                </div>

                {SHOP_ITEMS.map(item => {
                  const isUnlocked = unlockedShopItems.includes(item.id);
                  const isActive = item.type === 'Music' ? activeMusic === item.id : activeVisual === item.id;
                  return (
                    <div key={item.id} className="d-shop-item" style={{ borderColor: isActive ? item.accent : 'rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', minWidth: 0 }}>
                        <div className="d-shop-item-icon" style={{ color: item.accent, background: `${item.accent}22` }}>
                          {item.type === 'Music' ? <IconMusic /> : <IconSparkle />}
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <div className="d-shop-item-title">{item.name}</div>
                          <div className="d-shop-item-desc">{item.description}</div>
                          {!isUnlocked && (
                            <div className="d-shop-price">
                              <IconSparkle size={12} /> {item.cost} XP
                            </div>
                          )}
                          {isUnlocked && <div className="d-shop-owned">Unlocked</div>}
                        </div>
                      </div>
                      <div>
                        {isActive ? (
                          <button className="d-btn d-btn--secondary" disabled style={{ background: 'transparent', border: `1px solid ${item.accent}`, color: item.accent }}>Active</button>
                        ) : isUnlocked ? (
                          <button className="d-btn" onClick={() => equipShopItem(item)} style={{ background: item.accent, color: item.accent === '#fbbf24' ? '#111' : '#fff' }}>Use</button>
                        ) : (
                          <button className="d-btn" onClick={() => buyShopItem(item.id, item.cost)} style={{ background: '#fbbf24', color: 'black' }}>
                            Buy
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </main>
      </div>

      {floatingEmojis.map(f => (
        <div key={f.id} className={`d-floating-emoji ${f.type}`} style={{ left: f.x - 16, top: f.y - 16 }}>
          {f.emoji}
        </div>
      ))}

      {/* ══ ADD TASK MODAL ══ */}
      {showAddTaskModal && (
        <div className="d-modal-overlay fade-in" onClick={() => setShowAddTaskModal(false)}>
          <div className="d-modal-content" onClick={e => e.stopPropagation()}>
            <div className="d-modal-header">
              <h2 className="d-h1">{addTaskView === 'options' ? t('bubble.newTask') : (addTaskView === 'manual' ? t('bubble.manualEntry') : t('bubble.aiSmartInput'))}</h2>
              <button className="d-modal-close" onClick={() => setShowAddTaskModal(false)}>
                <IconClose />
              </button>
            </div>

            {addTaskView === 'options' && (
              <div className="d-modal-options">
                <button className="d-modal-btn" onClick={() => setAddTaskView('ai')}>
                  <div className="d-modal-icon" style={{ background: 'rgba(167,139,250,.15)', color: '#a78bfa' }}><IconSparkle /></div>
                  <div className="d-modal-text">
                    <strong>{t('bubble.aiSmartInput')}</strong>
                    <span>{t('bubble.aiSmartInputDesc')}</span>
                  </div>
                </button>
                <button className="d-modal-btn" onClick={isRecording ? stopRecording : startRecording}>
                  <div className="d-modal-icon" style={{ background: isRecording ? 'rgba(239,68,68,.15)' : 'rgba(56,189,248,.15)', color: isRecording ? '#ef4444' : '#38bdf8' }}>
                    {isRecording ? <div className="b-dot" style={{ background: '#ef4444', width: 12, height: 12, borderRadius: '50%' }} /> : <IconMic />}
                  </div>
                  <div className="d-modal-text">
                    <strong>{isRecording ? "Recording... Click to stop" : t('bubble.voiceMemo')}</strong>
                    <span>{t('bubble.voiceMemoDesc')}</span>
                  </div>
                </button>
                <button className="d-modal-btn" onClick={() => setAddTaskView('manual')}>
                  <div className="d-modal-icon" style={{ background: 'rgba(249,115,22,.15)', color: '#f97316' }}><IconKeyboard /></div>
                  <div className="d-modal-text">
                    <strong>{t('bubble.manualEntry')}</strong>
                    <span>{t('bubble.manualEntryDesc')}</span>
                  </div>
                </button>
              </div>
            )}

            {addTaskView === 'ai' && (
              <div className="d-modal-form">
                <textarea className="d-input" style={{ minHeight: '120px', resize: 'vertical' }} placeholder="Type or paste your unstructured task here..." value={aiText} onChange={e => setAiText(e.target.value)} autoFocus />
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                  <button className="d-btn d-btn--secondary" onClick={() => setAddTaskView('options')} style={{ flex: 1 }}>Back</button>
                  <button className="d-btn d-btn--primary" onClick={() => submitNewTask('ai')} disabled={isSubmittingTask || !aiText.trim()} style={{ flex: 2 }}>
                    {isSubmittingTask ? 'Processing...' : 'Extract & Add Task'}
                  </button>
                </div>
              </div>
            )}

            {addTaskView === 'manual' && (
              <div className="d-modal-form">
                <input className="d-input" placeholder={t('bubble.taskPlaceholder')} value={taskData.title} onChange={e => setTaskData({...taskData, title: e.target.value})} autoFocus />
                <input className="d-input" placeholder={t('bubble.durationPlaceholder')} value={taskData.duration} onChange={e => setTaskData({...taskData, duration: e.target.value})} />
                <input className="d-input" placeholder={t('bubble.dueDatePlaceholder')} value={taskData.due} onChange={e => setTaskData({...taskData, due: e.target.value})} />
                <textarea className="d-input" placeholder={t('bubble.notesPlaceholder')} value={taskData.notes} onChange={e => setTaskData({...taskData, notes: e.target.value})} />
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                  <button className="d-btn d-btn--secondary" onClick={() => setAddTaskView('options')} style={{ flex: 1 }}>Back</button>
                  <button className="d-btn d-btn--primary" onClick={() => submitNewTask('manual')} disabled={isSubmittingTask || !taskData.title.trim()} style={{ flex: 2 }}>
                    {isSubmittingTask ? 'Saving...' : t('bubble.createTask')}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
