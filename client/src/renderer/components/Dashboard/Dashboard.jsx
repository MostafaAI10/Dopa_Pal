import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import api from '../../services/api';
import { useLanguage } from '../../contexts/LanguageContext';
import { THEMES, applyTheme } from '../../themes';

/* ─── Helpers ───────────────────────────────────────────── */
const IS_ELECTRON = typeof window !== 'undefined' && !!window.electronAPI;

/* ─── API base URL for direct fetch calls (voice upload) ── */
const API_BASE_URL = typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL
  ? import.meta.env.VITE_API_BASE_URL : 'http://localhost:8000/api/v1';

/* ─── Duration parser utility ────────────────────────────── */
function parseDuration(durationInput) {
  if (!durationInput || !durationInput.trim()) return 2.0;

  const input = durationInput.trim().toLowerCase();

  // Common duration patterns and their hour equivalents
  const durationPatterns = {
    '15m': 0.25,
    '15 minutes': 0.25,
    '30m': 0.5,
    '30 minutes': 0.5,
    '45m': 0.75,
    '45 minutes': 0.75,
    '1h': 1.0,
    '1 hour': 1.0,
    '2h': 2.0,
    '2 hours': 2.0,
    'half day': 4.0,
    'half-day': 4.0,
    'half a day': 4.0,
    'full day': 8.0,
    'full-day': 8.0,
    'full a day': 8.0,
    'quick': 0.5,
    'short': 1.0,
    'small': 1.0,
    'big': 6.0,
    'huge': 10.0,
    'massive': 12.0,
    'q': 0.5,
    's': 1.0,
    'b': 6.0,
    'h': 10.0,
  };

  // Check for exact matches first
  if (input in durationPatterns) {
    return durationPatterns[input];
  }

  // Parse hours pattern (e.g., "1.5 hours", "2 hours")
  const hoursMatch = input.match(/(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)/);
  if (hoursMatch) {
    return parseFloat(hoursMatch[1]);
  }

  // Parse minutes pattern (e.g., "90 minutes", "45 mins")
  const minutesMatch = input.match(/(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)/);
  if (minutesMatch) {
    return parseFloat(minutesMatch[1]) / 60.0;
  }

  // Parse number with unit (e.g., "1.5h", "90m")
  const numberMatch = input.match(/^(\d+(?:\.\d+)?)(h|m|hour|min)?$/);
  if (numberMatch) {
    const val = parseFloat(numberMatch[1]);
    const unit = numberMatch[2];
    if (unit && unit.startsWith('m')) {
      return val / 60.0;
    } else if (unit && unit.startsWith('h')) {
      return val;
    } else {
      // No unit: assume minutes if > 10, else hours
      return val > 10 ? val / 60.0 : val;
    }
  }

  // Check for fractional durations (e.g., "half hour", "quarter day")
  const fractionalPatterns = [
    { regex: /half hour/i, value: 0.5 },
    { regex: /quarter hour/i, value: 0.25 },
    { regex: /half day/i, value: 4.0 },
    { regex: /quarter day/i, value: 1.0 },
    { regex: /third day/i, value: 8.0 / 3 },
    { regex: /tenth day/i, value: 0.8 },
  ];

  for (const pattern of fractionalPatterns) {
    if (pattern.regex.test(input)) {
      return pattern.value;
    }
  }

  // If all parsing attempts fail, return default
  return 2.0;
}

/* ─── Mock data (replace with real API later) ───────────── */
const USER = {
  name: 'Anchor User',
  email: 'user@anchor.app',
  avatar: '🧠',
  streak: 7,
  level: 'Focus Apprentice',
  xp: 340,
  xpMax: 500,
};

const TASKS = [
  { id: 1, title: 'Review project proposal', due: 'Today', priority: 'high', done: false },
  { id: 2, title: 'Reply to team emails', due: 'Today', priority: 'medium', done: false },
  { id: 3, title: 'Read chapter 3 of book', due: 'Tomorrow', priority: 'low', done: false },
  { id: 4, title: 'Weekly planning session', due: 'Today', priority: 'high', done: true },
  { id: 5, title: 'Update progress tracker', due: 'This week', priority: 'medium', done: true },
];

const RECOMMEND = {
  title: 'Reply to team emails',
  reason: 'You tend to work best on communication tasks in the evening. This has been waiting 2 days.',
  energy: 'Low',
  time: '15 min',
};

/* ─── Icons ─────────────────────────────────────────────── */
const Svg = ({ children, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);
const IconHome = () => <Svg><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></Svg>;
const IconTask = () => <Svg><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></Svg>;
const IconUser = () => <Svg><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></Svg>;
const IconSparkle = () => <Svg><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z" /></Svg>;
const IconMaximize = () => <Svg><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /></Svg>;
const IconClose = () => <Svg><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></Svg>;
const IconCheck = () => <Svg size={16}><polyline points="20 6 9 17 4 12" /></Svg>;
const IconEdit = () => <Svg size={16}><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></Svg>;
const IconTrash = () => <Svg size={16}><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></Svg>;
const IconPlus = () => <Svg><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" /><line x1="8" y1="12" x2="16" y2="12" /></Svg>;
const IconMinus = () => <Svg><line x1="5" y1="12" x2="19" y2="12" /></Svg>;
const IconMic = () => <Svg><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /><line x1="8" y1="22" x2="16" y2="22" /></Svg>;
const IconKeyboard = () => <Svg><rect width="20" height="16" x="2" y="4" rx="2" ry="2" /><line x1="6" x2="6.01" y1="8" y2="8" /><line x1="10" x2="10.01" y1="8" y2="8" /><line x1="14" x2="14.01" y1="8" y2="8" /><line x1="18" x2="18.01" y1="8" y2="8" /><line x1="8" x2="16" y1="12" y2="12" /><line x1="6" x2="6.01" y1="16" y2="16" /><line x1="10" x2="10.01" y1="16" y2="16" /><line x1="14" x2="14.01" y1="16" y2="16" /><line x1="18" x2="18.01" y1="16" y2="16" /></Svg>;
const IconFire = () => <Svg><path d="M12 2c0 0-5 5-5 10a5 5 0 0 0 10 0C17 7 12 2 12 2z" /></Svg>;
const IconSettings = () => <Svg><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></Svg>;
const IconLink = () => <Svg><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.07 0l-3 3A5 5 0 0 0 11 21.07l1.71-1.71" /></Svg>;
const IconShop = () => <Svg><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></Svg>;
const IconSync = () => <Svg><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16" /><path d="M3 21v-5h5" /><path d="M3 12A9 9 0 0 1 18.5 5.7L21 8" /><path d="M21 3v5h-5" /></Svg>;
const IconMusic = () => <Svg><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></Svg>;
const IconSend = () => <Svg size={18}><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></Svg>;
const IconBell = () => <Svg><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></Svg>;
const IconShield = () => <Svg><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></Svg>;
const IconGlobe = () => <Svg><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></Svg>;
const IconMail = () => <Svg size={14}><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M22 4L12 13 2 4" /></Svg>;
const IconChecklist = () => <Svg size={14}><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="9" y1="9" x2="15" y2="9" /><line x1="9" y1="13" x2="15" y2="13" /><line x1="9" y1="17" x2="13" y2="17" /></Svg>;

/* ── Brand icons (inline SVGs with brand colors) ── */
const GoogleLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);
const GmailLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path fill="#EA4335" d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.9 12 9.548 18.545 4.9l1.528-1.407C21.691 2.28 24 3.434 24 5.457z" />
  </svg>
);
const CalendarLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path fill="#4285F4" d="M3 3h18v18H3z" />
    <path fill="#fff" d="M3 3h18v4H3z" />
    <path fill="#fff" d="M3 7h18v4H3z" opacity="0" />
    <rect x="7" y="2" width="2" height="5" rx="1" fill="#fff" />
    <rect x="15" y="2" width="2" height="5" rx="1" fill="#fff" />
    <text x="12" y="18" textAnchor="middle" fill="#fff" fontSize="10" fontWeight="bold" fontFamily="Arial">1</text>
  </svg>
);
const NotionLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <rect width="24" height="24" rx="4" fill="#fff" />
    <path fill="#000" d="M4 5.5c0-.8.6-1.2 1.6-1.3l12.4-1c.9 0 1.4.3 1.4 1v13.6c0 .8-.6 1.3-1.5 1.4l-12.5 1c-.8 0-1.4-.3-1.4-1V5.5z" opacity="0.9" />
    <path fill="#fff" d="M6.7 6.3l7.5-.6v11.7l-7.5.6V6.3z" />
    <path fill="#000" d="M10.5 7.3l4.5-.4v9.9l-4.5.4V7.3z" opacity="0.2" />
    <path fill="#fff" d="M7.8 6.6l2.7-.2v10.5l-2.7.2V6.6z" />
  </svg>
);
const TaskListLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M9 8h6" />
    <path d="M9 12h6" />
    <path d="M9 16h4" />
    <path d="M7 8l1 1 2-2" strokeWidth="2.5" opacity="0.7" />
  </svg>
);

const SchemaSelect = ({ label, schema, types, value, onChange, placeholder, help }) => {
  const filtered = (schema || []).filter(p => types.includes(p.type));
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontSize: 13, color: 'var(--text2)' }}>{label}</span>
      {help && <p className="d-field-help" style={{ margin: 0 }}>{help}</p>}
      {filtered.length > 0 ? (
        <select className="d-input" style={{ appearance: 'auto' }} value={value} onChange={e => onChange(e.target.value)}>
          <option value="">{placeholder || '— Select —'}</option>
          {filtered.map(p => (
            <option key={p.name} value={p.name}>{p.name} ({p.type})</option>
          ))}
        </select>
      ) : (
        <input className="d-input" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder || 'Type column name'} />
      )}
    </label>
  );
};

/* ─── Themes Store (imported from themes.js) ─────────────── */

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
  { id: 'google', name: 'Google', accent: '#38bdf8', logo: '/integrations/google.svg', apps: ['Tasks', 'Calendar', 'Gmail'], tokenLabel: 'OAuth access token', settingLabel: 'Account email', settingKey: 'email' },
  { id: 'notion', name: 'Notion', accent: '#f8fafc', logo: '/integrations/notion.svg', apps: ['Databases', 'Tasks'], tokenLabel: 'Integration token', settingLabel: 'Database ID', settingKey: 'database_id' },
  { id: 'jira', name: 'Jira', accent: '#60a5fa', logo: '/integrations/jira.svg', apps: ['Issues', 'Projects'], tokenLabel: 'API token', settingLabel: 'Project key', settingKey: 'project_key' },
  { id: 'canvas', name: 'Canvas LMS', accent: '#fb7185', logo: '/integrations/canvas.svg', apps: ['Assignments', 'Courses'], tokenLabel: 'Access token', settingLabel: 'Course ID', settingKey: 'course_id' },
];

/* ─── PINCH categories — single source of truth (no emojis) ── */
const PINCH_CATEGORIES = [
  { id: 'passion', label: 'Passion', color: '#ec4899' },
  { id: 'interest', label: 'Interest', color: '#38bdf8' },
  { id: 'novelty', label: 'Novelty', color: '#fb923c' },
  { id: 'challenge', label: 'Challenge', color: '#22c55e' },
  { id: 'hurry', label: 'Hurry', color: '#ef4444' },
];
const PINCH_BY_ID = Object.fromEntries(PINCH_CATEGORIES.map(c => [c.id, c]));

const _daysUntil = (deadlineRaw) => {
  if (!deadlineRaw) return Infinity;
  const ms = new Date(deadlineRaw).getTime() - Date.now();
  return ms / 86400000;
};

/**
 * Deterministic, single-category mapping used for BOTH coloring and
 * filtering, so the two never disagree. Precedence: time pressure first,
 * then heavy lifts, then engagement, then novelty as the default.
 */
function getPinchCategory(task) {
  const score = task.pinchScore ?? 50;
  const hours = task.estimatedHours ?? 0;
  if (_daysUntil(task.deadlineRaw) <= 1) return 'hurry';
  if (hours >= 4 && score >= 60) return 'challenge';
  if (task.interestTag && score >= 70) return 'passion';
  if (task.interestTag) return 'interest';
  return 'novelty';
}

const matchesPinch = (task, filter) => filter === 'all' || getPinchCategory(task) === filter;

/* ─── PINCH category tag (colored chip, no emoji) ───────────── */
const PinchTag = ({ category }) => {
  const cat = PINCH_BY_ID[category];
  if (!cat) return null;
  return (
    <span
      className="d-pinch-tag"
      style={{ color: cat.color, borderColor: cat.color + '66', background: cat.color + '1f' }}
    >
      {cat.label}
    </span>
  );
};

/* ─── PINCH filter bar (data-driven, colored, no emoji) ─────── */
const PinchFilterBar = ({ value, onChange }) => (
  <div className="d-pinch-filter">
    <span className="d-pinch-filter-label">Filter by PINCH</span>
    <button
      className={`d-pinch-pill${value === 'all' ? ' active' : ''}`}
      onClick={() => onChange('all')}
    >
      All
    </button>
    {PINCH_CATEGORIES.map(cat => (
      <button
        key={cat.id}
        className={`d-pinch-pill${value === cat.id ? ' active' : ''}`}
        onClick={() => onChange(cat.id)}
        style={value === cat.id
          ? { background: cat.color + '33', borderColor: cat.color, color: 'var(--text-white)' }
          : { borderColor: cat.color + '80', color: cat.color }}
      >
        {cat.label}
      </button>
    ))}
  </div>
);

/* ─── Priority badge ────────────────────────────────────── */
const PriorityBadge = ({ level }) => (
  <span className={`d-badge d-badge--${level}`}>{level.toUpperCase()}</span>
);

/* ─── Task row ──────────────────────────────────────────── */
const TaskRow = ({ task, onToggle, onDelete, onUpdateTask, onToggleSub, onUndoSub, onUpdateSub, isDeleting }) => {
  const category = getPinchCategory(task);
  const catColor = PINCH_BY_ID[category].color;
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editPriority, setEditPriority] = useState(task.priority);
  const [editDeadline, setEditDeadline] = useState(
    task.deadlineRaw ? new Date(task.deadlineRaw).toISOString().slice(0, 16) : ''
  );
  const [editDuration, setEditDuration] = useState(task.estimatedHours ?? '');
  const [editingSubId, setEditingSubId] = useState(null);
  const [editSubTitle, setEditSubTitle] = useState('');

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
      <div className="d-task d-task--editing" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '10px', background: 'var(--accent-dim)', borderColor: 'var(--accent)', padding: '14px 16px' }}>
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
            style={{ cursor: 'pointer', outline: 'none', border: '1px solid var(--border)', padding: '4px 10px', flexShrink: 0 }}
          >
            <option style={{ color: 'black' }} value="high">HIGH</option>
            <option style={{ color: 'black' }} value="medium">MEDIUM</option>
            <option style={{ color: 'black' }} value="low">LOW</option>
          </select>
        </div>
        {/* Row 2: Deadline + Duration */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>📅 Deadline</label>
            <input
              type="datetime-local"
              value={editDeadline}
              onChange={e => setEditDeadline(e.target.value)}
              className="d-input"
              style={{ padding: '6px 10px', fontSize: '13px', margin: 0, height: 'auto', colorScheme: 'dark' }}
            />
          </div>
          <div style={{ width: '130px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>⏱️ Duration (hrs)</label>
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

  const subs = task.subBlocks || [];
  const doneSubs = subs.filter(b => b.status === 'completed').length;

  return (
    <div
      className={`d-task d-task--card${task.done ? ' d-task--done' : ''}${isDeleting ? ' d-task--deleting' : ''}`}
      style={{ '--cat': catColor }}
    >
      <span className="d-task-cat-bar" />
      <div className="d-task-head">
        <button className={`d-task-check${task.done ? ' checked' : ''}`} onClick={() => onToggle(task.id)}>
          {task.done && <IconCheck />}
        </button>
        <div className="d-task-body">
          <div className="d-task-title-row">
            <span className="d-task-title">{task.title}</span>
            <PinchTag category={category} />
          </div>
          <div className="d-task-meta">
            <span className="d-task-meta-item">{task.due}</span>
            {task.estimatedHours != null && (
              <span className="d-task-meta-item">{task.estimatedHours}h</span>
            )}
            {task.interestTag && (
              <span className="d-task-meta-item d-task-meta-tag">{task.interestTag}</span>
            )}
            {subs.length > 0 && (
              <span className="d-task-meta-item">{doneSubs}/{subs.length} steps</span>
            )}
          </div>
        </div>
        <div className="d-task-actions">
          <PriorityBadge level={task.priority} />
          {!task.done && (
            <button className="d-task-icon-btn" onClick={() => setIsEditing(true)} title="Edit task">
              <IconEdit />
            </button>
          )}
          <button className="d-task-icon-btn d-task-icon-btn--danger" onClick={() => onDelete(task.id)} title="Delete task">
            <IconTrash />
          </button>
        </div>
      </div>

      {/* Sub-tasks as interactive mini-modules */}
      {subs.length > 0 && (
        <div className="d-submods">
          {subs.map((block) => {
            const done = block.status === 'completed';
            const isSubEditing = editingSubId === block.id;
            return (
              <div
                key={block.id ?? block.sequence}
                className={`d-submod${done ? ' d-submod--done' : ''}`}
                style={{ cursor: done ? 'default' : 'pointer' }}
              >
                <button
                  className="d-submod-check"
                  onClick={() => done
                    ? onUndoSub && onUndoSub(task.id, block)
                    : onToggleSub && onToggleSub(task.id, block)
                  }
                  title={done ? 'Undo completion' : 'Mark step complete'}
                  style={{ background: 'transparent', border: 'none', padding: 0, cursor: 'pointer' }}
                >
                  {done ? <IconCheck /> : block.sequence}
                </button>
                <span className="d-submod-body" onDoubleClick={() => {
                  if (!done) {
                    setEditingSubId(block.id);
                    setEditSubTitle(block.title || '');
                  }
                }}>
                  {isSubEditing ? (
                    <input
                      className="d-submod-edit"
                      value={editSubTitle}
                      onChange={e => setEditSubTitle(e.target.value)}
                      onBlur={() => {
                        if (editSubTitle.trim() && editSubTitle !== block.title) {
                          onUpdateSub && onUpdateSub(block.id, { title: editSubTitle.trim() });
                        }
                        setEditingSubId(null);
                      }}
                      onKeyDown={e => {
                        if (e.key === 'Enter') e.target.blur();
                        if (e.key === 'Escape') { setEditingSubId(null); }
                      }}
                      autoFocus
                    />
                  ) : (
                    <span className="d-submod-title">{block.title || `Step ${block.sequence}`}</span>
                  )}
                  <span className="d-submod-meta">
                    {block.duration_minutes}m · {new Date(block.scheduled_date).toLocaleDateString()}
                  </span>
                </span>
                {done && (
                  <button
                    className="d-submod-undo"
                    onClick={() => onUndoSub && onUndoSub(task.id, block)}
                    title="Undo completion"
                  >
                    Undo
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Source badge ── */}
      {task.sourceType && (
        <div className="d-task-source" title={task.rawSourceText ? task.rawSourceText : task.sourceType}>
          {task.sourceType === 'manual' && <><IconKeyboard /><span>Manual</span></>}
          {task.sourceType === 'voice' && <><IconMic /><span>Voice</span></>}
          {task.sourceType === 'ai' && <><IconSparkle /><span>AI</span></>}
          {task.sourceType === 'calendar' && <><CalendarLogo size={12} /><span>Google Calendar</span></>}
          {task.sourceType === 'google_tasks' && <><IconChecklist /><span>Google Tasks</span></>}
          {task.sourceType === 'gmail' && <><IconMail /><span>Gmail</span></>}
          {task.sourceType === 'notion' && <><NotionLogo size={12} /><span>Notion</span></>}
          {task.sourceType === 'highlight' && <><IconSparkle /><span>Highlight</span></>}
        </div>
      )}
    </div>
  );
};

const MarkdownRenderer = ({ content }) => {
  if (!content) return null;
  const blocks = content.split('\n');

  return (
    <div className="d-chat-msg-text">
      {blocks.map((line, idx) => {
        // Headers
        if (line.startsWith('### ')) {
          return <h4 key={idx} style={{ color: 'var(--accent)', marginTop: '8px', marginBottom: '4px', fontSize: '15px' }}>{line.replace('### ', '')}</h4>;
        }
        if (line.startsWith('## ')) {
          return <h3 key={idx} style={{ color: 'var(--med)', marginTop: '12px', marginBottom: '6px', fontSize: '16px' }}>{line.replace('## ', '')}</h3>;
        }
        if (line.startsWith('# ')) {
          return <h2 key={idx} style={{ color: 'var(--success)', marginTop: '16px', marginBottom: '8px', fontSize: '18px' }}>{line.replace('# ', '')}</h2>;
        }

        // Render bold text
        const renderInline = (text) => {
          const parts = text.split(/(\*\*.*?\*\*)/g);
          return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={i} style={{ color: 'var(--text-white)' }}>{part.slice(2, -2)}</strong>;
            }
            return <span key={i} style={{ color: 'var(--text)' }}>{part}</span>;
          });
        };

        // Bullet points
        if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
          return (
            <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '4px', paddingLeft: '8px' }}>
              <span style={{ color: 'var(--accent)' }}>•</span>
              <span>{renderInline(line.replace(/^[-*]\s/, ''))}</span>
            </div>
          );
        }

        // Numbered lists
        const numMatch = line.trim().match(/^(\d+\.)\s(.*)/);
        if (numMatch) {
          return (
            <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '4px', paddingLeft: '8px' }}>
              <strong style={{ color: 'var(--accent)' }}>{numMatch[1]}</strong>
              <span>{renderInline(numMatch[2])}</span>
            </div>
          );
        }

        if (line.trim() === '') return <div key={idx} style={{ height: '8px' }} />;

        return <div key={idx} style={{ marginBottom: '4px' }}>{renderInline(line)}</div>;
      })}
    </div>
  );
};

/* ── ChipInput ─────────────────────────────────────────── */
const ChipInput = ({ values = [], onChange, placeholder }) => {
  const [input, setInput] = useState('');
  const inputRef = useRef(null);

  const add = (val) => {
    const v = val.trim().toLowerCase();
    if (v && !values.includes(v)) {
      onChange([...values, v]);
    }
  };

  const remove = (idx) => {
    const copy = [...values];
    copy.splice(idx, 1);
    onChange(copy);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      add(input);
      setInput('');
    }
    if (e.key === 'Backspace' && !input && values.length) {
      remove(values.length - 1);
    }
  };

  const handlePaste = (e) => {
    const text = e.clipboardData.getData('text');
    if (text.includes(',') || text.includes('\n')) {
      e.preventDefault();
      const parts = text.split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
      const combined = [...values, ...parts.map(v => v.toLowerCase())];
      onChange([...new Set(combined)]);
    }
  };

  return (
    <div className="d-chip-input" onClick={() => inputRef.current?.focus()}>
      {values.map((v, i) => (
        <span key={i} className="d-chip-item">
          <span>{v}</span>
          <button className="d-chip-remove" onClick={() => remove(i)}>×</button>
        </span>
      ))}
      <input
        ref={inputRef}
        className="d-chip-field"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKey}
        onPaste={handlePaste}
        placeholder={values.length ? '' : placeholder}
      />
    </div>
  );
};

/* ══════════════════════════════════════════════════════════
   DASHBOARD COMPONENT
   ══════════════════════════════════════════════════════════ */
export default function Dashboard() {
  const { t, lang, changeLanguage, isRTL } = useLanguage();
  const chatEndRef = useRef(null);
  const [tab, setTab] = useState('home');
  const [tasks, setTasks] = useState([]);
  const [bubbleTask, setBubbleTask] = useState(null);
  const [pinchFilter, setPinchFilter] = useState('all'); // 'all', 'passion', 'interest', 'novelty', 'challenge', 'hurry'

  // Delete flow (confirm prompt + exit animation) and background toasts
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deletingIds, setDeletingIds] = useState(() => new Set());
  const [toasts, setToasts] = useState([]);
  const toastSeq = useRef(0);
  const lastSyncAtRef = useRef(null);

  const pushToast = (text, kind = 'info', ttl = 2600) => {
    const id = ++toastSeq.current;
    setToasts(ts => [...ts, { id, text, kind }]);
    if (ttl) setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), ttl);
    return id;
  };
  const updateToast = (id, text, kind) =>
    setToasts(ts => ts.map(t => (t.id === id ? { ...t, text, kind } : t)));
  const dismissToast = (id, delay = 2200) =>
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), delay);

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
  const [isVoiceTask, setIsVoiceTask] = useState(false);
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
  const [integrationSaving, setIntegrationSaving] = useState(null); // provider id string or null
  const [integrationMessage, setIntegrationMessage] = useState('');
  const [syncSettingsModal, setSyncSettingsModal] = useState(null);
  const [syncSettingsClosing, setSyncSettingsClosing] = useState(false);
  const [syncSettingsData, setSyncSettingsData] = useState({});
  const [syncSettingsDraft, setSyncSettingsDraft] = useState({});
  const [syncSettingsLoading, setSyncSettingsLoading] = useState(false);
  const [syncSettingsSaving, setSyncSettingsSaving] = useState(false);
  const [availableDatabases, setAvailableDatabases] = useState([]);
  const [notionDatabasesLoading, setNotionDatabasesLoading] = useState(false);
  const [notionSchema, setNotionSchema] = useState(null);
  const [notionSchemaLoading, setNotionSchemaLoading] = useState(false);

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
  const [settingsPage, setSettingsPage] = useState(null); // null = grid, or section id

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

    // Sync unlocked rewards from backend, merging with localStorage
    api.getUnlockedRewards().then(rewards => {
      const themeIds = rewards
        .filter(r => r.type === 'theme' && r.metadata_json?.item_id)
        .map(r => r.metadata_json.item_id);
      const shopIds = rewards
        .filter(r => r.type === 'shop_item' && r.metadata_json?.item_id)
        .map(r => r.metadata_json.item_id);
      if (themeIds.length > 0) {
        setUnlockedThemes(prev => {
          const merged = [...new Set([...prev, ...themeIds])];
          localStorage.setItem('dopapal_themes_v3', JSON.stringify(merged));
          return merged;
        });
      }
      if (shopIds.length > 0) {
        setUnlockedShopItems(prev => {
          const merged = [...new Set([...prev, ...shopIds])];
          localStorage.setItem('dopapal_shop_items_v1', JSON.stringify(merged));
          return merged;
        });
      }
    }).catch(() => {});

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
    applyTheme(activeTheme);
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
      api.purchaseReward('theme', themeId).catch(() => {});
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
      api.purchaseReward('shop_item', itemId).catch(() => {});
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
        .catch(() => { });
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

    setIntegrationSaving(provider.id);
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
      setIntegrationSaving(null);
    }
  };

  const connectGoogle = async () => {
    if (IS_ELECTRON && window.electronAPI.startGoogleOAuth) {
      setIntegrationSaving('google');
      setIntegrationMessage('');
      try {
        const result = await window.electronAPI.startGoogleOAuth();
        if (result.success) {
          setIntegrationMessage('Google connected successfully!');
          await fetchIntegrations();
        } else {
          setIntegrationMessage(result.error || 'Connection failed.');
        }
      } catch (err) {
        console.error('Google OAuth error:', err);
        setIntegrationMessage('Could not connect Google. Check the backend logs.');
      } finally {
        setIntegrationSaving(null);
      }
    } else {
      setIntegrationMessage('Google OAuth is only available in the desktop app.');
    }
  };

  const disconnectGoogle = async () => {
    setIntegrationSaving('google');
    try {
      await api.delete('/integrations/config/google');
      pushToast('Google disconnected', 'success');
      await fetchIntegrations();
    } catch (err) {
      console.error('Disconnect error:', err);
      pushToast('Failed to disconnect', 'error');
    } finally {
      setIntegrationSaving(null);
    }
  };

  // ── Notion connection (OAuth popup, same UX as Google) ───────────
  const connectNotion = async () => {
    if (IS_ELECTRON && window.electronAPI.startNotionOAuth) {
      setIntegrationSaving('notion');
      setIntegrationMessage('');
      try {
        const result = await window.electronAPI.startNotionOAuth();
        if (result.success) {
          pushToast('Notion connected!', 'success');
          await fetchIntegrations();
          openSyncSettings('notion');
        } else {
          setIntegrationMessage(result.error || 'Connection failed.');
        }
      } catch (err) {
        console.error('Notion OAuth error:', err);
        setIntegrationMessage('Could not connect Notion. Check the backend logs.');
      } finally {
        setIntegrationSaving(null);
      }
    } else {
      // Browser fallback: open OAuth URL in a new tab
      try {
        const { url } = await api.get('/auth/notion/url');
        if (url) {
          window.open(url, '_blank', 'width=600,height=700');
          setIntegrationMessage('Complete authorization in the opened tab, then refresh.');
        } else {
          setIntegrationMessage('Notion OAuth is not configured on the server.');
        }
      } catch (err) {
        console.error('Notion OAuth error:', err);
        setIntegrationMessage('Could not start Notion authorization.');
      }
    }
  };

  const disconnectNotion = async () => {
    setIntegrationSaving('notion');
    try {
      await api.delete('/integrations/config/notion');
      pushToast('Notion disconnected', 'success');
      setSyncSettingsData({});
      await fetchIntegrations();
    } catch (err) {
      console.error('Disconnect error:', err);
      pushToast('Failed to disconnect', 'error');
    } finally {
      setIntegrationSaving(null);
    }
  };

  // ── Sync settings (Google + Notion) ──────────────────────────────

  const loadSyncSettings = async (provider) => {
    setSyncSettingsLoading(true);
    try {
      if (provider === 'notion') {
        const res = await api.get('/sync/notion/settings');
        const s = res.settings || {};
        setSyncSettingsData(s);
        setSyncSettingsDraft(JSON.parse(JSON.stringify(s)));
        // fetch available databases for the picker
        setNotionDatabasesLoading(true);
        try {
          const dbRes = await api.get('/sync/notion/databases');
          setAvailableDatabases(dbRes.databases || []);
        } catch (e) {
          console.warn('Could not fetch Notion databases', e);
          setAvailableDatabases([]);
        } finally {
          setNotionDatabasesLoading(false);
        }
        // fetch schema for the saved database ID
        if (s.notion_database_id) {
          setNotionSchemaLoading(true);
          try {
            const schemaRes = await api.get(`/sync/notion/database-schema?database_id=${s.notion_database_id}`);
            setNotionSchema(schemaRes.properties || []);
          } catch (e) {
            console.warn('Could not fetch Notion database schema', e);
            setNotionSchema(null);
          } finally {
            setNotionSchemaLoading(false);
          }
        }
      } else {
        const res = await api.get('/sync/google/settings');
        const s = res.settings || {};
        setSyncSettingsData(s);
        setSyncSettingsDraft(JSON.parse(JSON.stringify(s)));
      }
    } catch (e) {
      console.error('Failed to load sync settings', e);
    } finally {
      setSyncSettingsLoading(false);
    }
  };

  const saveSyncSettings = async () => {
    setSyncSettingsSaving(true);
    try {
      const provider = syncSettingsModal;
      if (provider === 'notion') {
        await api.put('/sync/notion/settings', { settings: syncSettingsDraft });
      } else {
        await api.put('/sync/google/settings', { settings: syncSettingsDraft });
      }
      setSyncSettingsData(JSON.parse(JSON.stringify(syncSettingsDraft)));
      await fetchIntegrations();
      closeSyncSettings();
    } catch (e) {
      console.error('Failed to save sync settings', e);
    } finally {
      setSyncSettingsSaving(false);
    }
  };

  const closeSyncSettings = () => {
    setSyncSettingsClosing(true);
    setTimeout(() => {
      setSyncSettingsModal(null);
      setSyncSettingsClosing(false);
      setAvailableDatabases([]);
      setNotionSchema(null);
    }, 180);
  };

  const openSyncSettings = (provider) => {
    loadSyncSettings(provider);
    setSyncSettingsModal(provider);
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
        done: t.status === 'completed',
        interestTag: t.interest_tag,
        pinchScore: t.pinch_score,
        subBlocks: t.sub_blocks || [],
        sourceType: t.source_type || null,
        rawSourceText: t.raw_source_text || null
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

  // ── Poll background sync status ──
  useEffect(() => {
    const lastSyncRefs = { google: null, notion: null };
    const check = async () => {
      for (const provider of ['google', 'notion']) {
        try {
          const status = await api.get(`/sync/${provider}/status`);
          if (status.connected && status.last_synced_at) {
            const prev = lastSyncRefs[provider];
            lastSyncRefs[provider] = status.last_synced_at;
            if (prev && prev !== status.last_synced_at) {
              pushToast(`${provider.charAt(0).toUpperCase() + provider.slice(1)} data synced`, 'success');
              fetchTasksAndBubble();
            }
          }
        } catch {
          // not connected or offline — ignore
        }
      }
    };
    check();
    const interval = setInterval(check, 20000);
    return () => clearInterval(interval);
  }, []);

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
    // Background the work: close the modal right away and track via a toast,
    // so the user isn't held on a blocking "Saving…" screen.
    setShowAddTaskModal(false);
    setAddTaskView('options');
    const toastId = pushToast('Adding task…', 'loading', 0);
    try {
      if (source === 'manual') {
        // Use the server's duration parser for consistent parsing
        let hours = 2.0;

        if (taskData.duration && taskData.duration.trim()) {
          try {
            // Call the server's duration parser API
            const response = await fetch('/api/v1/parse-duration', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ duration: taskData.duration })
            });

            if (response.ok) {
              const result = await response.json();
              hours = result.hours;
            } else {
              // Fallback to client-side parsing if server API fails
              hours = parseDuration(taskData.duration);
            }
          } catch (error) {
            console.error("Failed to parse duration:", error);
            // Fallback to client-side parsing
            hours = parseDuration(taskData.duration);
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
          source_type: isVoiceTask ? 'voice' : 'highlight'
        };

        if (IS_ELECTRON) {
          await window.electronAPI.ingestTask(payload);
        } else {
          await api.ingestTask(payload.source_text, payload.source_type);
        }
      }

      setTaskData({ title: '', duration: '', due: '', notes: '' });
      setAiText('');
      setIsVoiceTask(false);
      await fetchTasksAndBubble();
      updateToast(toastId, 'Task added', 'success');
      dismissToast(toastId);
    } catch (e) {
      console.error("Failed to submit task:", e);
      updateToast(toastId, 'Could not add task — ' + (e?.message || 'try again'), 'error');
      dismissToast(toastId, 3600);
    } finally {
      setIsSubmittingTask(false);
    }
  };

  const recordingStartTime = useRef(0);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorder.current = recorder;
      audioChunks.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      recordingStartTime.current = Date.now();
      recorder.start();
      setIsRecording(true);
      // Keep showing the options menu, the button will change to a red recording dot
      setAddTaskView('options');
      console.log('[Voice] Recording started at', recordingStartTime.current);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      pushToast('Microphone access denied or error occurred.', 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.onstop = async () => {
        const duration = Date.now() - recordingStartTime.current;
        const totalBytes = audioChunks.current.reduce((sum, c) => sum + c.size, 0);
        console.log('[Voice] Recording stopped. Duration:', duration, 'ms | Chunks:', audioChunks.current.length, '| Total bytes:', totalBytes);
        
        if (audioChunks.current.length === 0) {
          console.warn('[Voice] No audio chunks recorded');
          setIsRecording(false);
          setIsSubmittingTask(false);
          return;
        }
        if (duration < 500) {
          console.warn('[Voice] Recording too short:', duration, 'ms');
          setIsRecording(false);
          setIsSubmittingTask(false);
          pushToast('Recording too short — please hold the button longer.', 'error');
          return;
        }
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        
        // Show loading state while processing voice
        setIsSubmittingTask(true);
        const toastId = pushToast('Analyzing voice with AI...', 'loading', 0);
        
        // Stop all tracks to release the mic
        mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
        
        // Submit the audio blob
        try {
          await submitVoiceTask(audioBlob);
          dismissToast(toastId);
        } catch (error) {
          console.error("Voice task failed:", error);
          updateToast(toastId, 'Failed to analyze voice', 'error');
          dismissToast(toastId, 3000);
        } finally {
          setIsSubmittingTask(false);
          audioChunks.current = [];
        }
      };
      
      mediaRecorder.current.stop();
      setIsRecording(false);
    }
  };

  const submitVoiceTask = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'voice_recording.webm');
      formData.append('source_type', 'voice');

      const response = await fetch(`${API_BASE_URL}/tasks/ingest-voice`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      const result = await response.json();
      console.log('[Voice] Ingestion successful:', result);
      
      // Reset forms and refresh
      setTaskData({ title: '', duration: '', due: '', notes: '' });
      setAiText('');
      setIsVoiceTask(false);
      await fetchTasksAndBubble();
    } catch (e) {
      console.error("Failed to submit voice task:", e);
      throw e;
    }
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

  // Delete is a two-step flow: ask for confirmation, then play an exit
  // animation before the row actually leaves and is persisted.
  const requestDelete = (id) => setConfirmDeleteId(id);

  const performDelete = async () => {
    const id = confirmDeleteId;
    if (id == null) return;
    setConfirmDeleteId(null);
    setDeletingIds(prev => new Set(prev).add(id));
    setTimeout(async () => {
      setTasks(ts => ts.filter(t => t.id !== id));
      setDeletingIds(prev => { const n = new Set(prev); n.delete(id); return n; });
      try {
        await api.deleteTask(id);
        pushToast('Task deleted', 'info');
      } catch (e) {
        console.error("Failed to delete task:", e);
        pushToast('Could not delete task', 'error', 3200);
      }
      fetchTasksAndBubble();
    }, 380); // keep in sync with the d-task--deleting animation
  };

  const toggleSubBlock = async (taskId, block) => {
    if (!block || block.status === 'completed') return;
    const key = block.id ?? block.sequence;
    const setStatus = (status) => setTasks(ts => ts.map(t => {
      if (t.id !== taskId) return t;
      return {
        ...t,
        subBlocks: (t.subBlocks || []).map(b =>
          (b.id ?? b.sequence) === key ? { ...b, status } : b),
      };
    }));

    setStatus('completed'); // optimistic — CSS plays the completion pop
    try {
      if (block.id != null) await api.completeSubBlock(block.id);
    } catch (e) {
      console.error('Failed to complete sub-block:', e);
      setStatus(block.status); // revert
      pushToast('Could not update step', 'error', 3000);
    }
  };

  const undoSubBlock = async (taskId, block) => {
    if (!block || block.status !== 'completed') return;
    const key = block.id ?? block.sequence;
    const revert = (status) => setTasks(ts => ts.map(t => {
      if (t.id !== taskId) return t;
      return {
        ...t,
        done: false,
        subBlocks: (t.subBlocks || []).map(b =>
          (b.id ?? b.sequence) === key ? { ...b, status, completedAt: null } : b),
      };
    }));

    revert('pending');
    try {
      if (block.id != null) await api.undoSubBlock(block.id);
    } catch (e) {
      console.error('Failed to undo sub-block:', e);
      revert('completed');
      pushToast('Could not undo step', 'error', 3000);
    }
  };

  const updateSubBlockTitle = async (subBlockId, updates) => {
    setTasks(ts => ts.map(t => ({
      ...t,
      subBlocks: (t.subBlocks || []).map(b =>
        b.id === subBlockId ? { ...b, ...updates } : b),
    })));

    try {
      await api.updateSubBlock(subBlockId, updates);
    } catch (e) {
      console.error('Failed to update sub-block:', e);
      pushToast('Could not update step', 'error', 3000);
    }
  };

  const updateTaskDetails = async (id, updates) => {
    const current = tasks.find(t => t.id === id);
    const payload = {};
    if (updates.title !== undefined) payload.title = updates.title;
    if (updates.deadline !== undefined) payload.deadline = updates.deadline;
    if (updates.estimatedHours !== undefined) payload.estimated_hours = updates.estimatedHours;
    // Only rewrite the PINCH score when the priority bucket actually changed,
    // so editing a title/deadline doesn't silently reset the score.
    if (updates.priority !== undefined && updates.priority !== current?.priority) {
      payload.pinch_score = updates.priority === 'high' ? 90.0
        : updates.priority === 'low' ? 20.0 : 50.0;
    }

    // Optimistic update so the row reflects the edit immediately.
    setTasks(ts => ts.map(t => t.id === id ? {
      ...t,
      title: updates.title ?? t.title,
      priority: updates.priority ?? t.priority,
      due: updates.deadline ? new Date(updates.deadline).toLocaleString() : t.due,
      deadlineRaw: updates.deadline ?? t.deadlineRaw,
      estimatedHours: updates.estimatedHours ?? t.estimatedHours,
    } : t));

    try {
      const saved = await api.updateTask(id, payload);
      // Trust the server's persisted row as the source of truth, so the UI
      // always shows the value the backend actually stored (fixes stale edits).
      if (saved && saved.id != null) {
        setTasks(ts => ts.map(t => t.id === id ? {
          ...t,
          title: saved.title ?? t.title,
          due: saved.deadline ? new Date(saved.deadline).toLocaleString() : t.due,
          deadlineRaw: saved.deadline ?? t.deadlineRaw,
          estimatedHours: saved.estimated_hours ?? t.estimatedHours,
          pinchScore: saved.pinch_score ?? t.pinchScore,
          priority: saved.pinch_score != null
            ? (saved.pinch_score >= 80 ? 'high' : saved.pinch_score < 40 ? 'low' : 'medium')
            : t.priority,
          interestTag: saved.interest_tag ?? t.interestTag,
        } : t));
      }
      pushToast('Task updated', 'success');
    } catch (e) {
      console.error("Failed to update task:", e);
      pushToast('Could not save changes', 'error', 3200);
      fetchTasksAndBubble(); // resync from server on failure
    }
  };

  const pending = tasks.filter(t => !t.done);
  const done = tasks.filter(t => t.done);

  // One filter, applied consistently everywhere (color + filter agree).
  const matchesFilter = (t) => matchesPinch(t, pinchFilter);
  const visibleAll = tasks.filter(matchesFilter);
  const visiblePending = pending.filter(matchesFilter);
  const visibleDone = done.filter(matchesFilter);

  const close = () => {
    if (IS_ELECTRON) window.electronAPI.closeDashboard();
    else window.history.back();
  };

  const maximize = () => {
    if (IS_ELECTRON) window.electronAPI.maximizeDashboard();
  };

  const minimize = () => {
    if (IS_ELECTRON) window.electronAPI.minimizeDashboard();
  };

  const handleSendChat = async () => {
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setIsTyping(true);

    try {
      const apiMessages = [...chatMessages, { sender: 'user', text: userMsg }].map(m => ({
        role: m.sender === 'ai' ? 'assistant' : 'user',
        content: m.text
      }));
      
      const response = await api.sendChatMessage(apiMessages);
      let aiText = '';
      if (typeof response === 'string') {
        aiText = response;
      } else if (response && response.text) {
        aiText = response.text;
      } else if (response && response.message) {
        aiText = response.message;
      } else if (response && response.reply) {
        aiText = response.reply;
      } else {
        aiText = JSON.stringify(response);
      }
      
      setChatMessages(prev => [...prev, { sender: 'ai', text: aiText }]);
      fetchTasksAndBubble();
    } catch (err) {
      console.error('Chat error:', err);
      setChatMessages(prev => [...prev, { sender: 'ai', text: 'Sorry, I am having trouble connecting to the brain.' }]);
    } finally {
      setIsTyping(false);
    }
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
              { id: 'home', label: t('dashboard.home'), Icon: IconHome },
              { id: 'tasks', label: t('dashboard.allTasks'), Icon: IconTask },
              { id: 'assistant', label: t('dashboard.assistant'), Icon: IconSparkle },
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
                {/* PINCH Filter */}
                <PinchFilterBar value={pinchFilter} onChange={setPinchFilter} />
                <div className="d-task-list">
                  {visibleAll.length === 0 ? (
                    <div className="d-task-empty">
                      No tasks match the current filter. Try a different PINCH category or reset to "All".
                    </div>
                  ) : visibleAll.map(t => (
                    <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={requestDelete}
                      onUpdateTask={updateTaskDetails} onToggleSub={toggleSubBlock}
                      onUndoSub={undoSubBlock} onUpdateSub={updateSubBlockTitle}
                      isDeleting={deletingIds.has(t.id)} />
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

              <PinchFilterBar value={pinchFilter} onChange={setPinchFilter} />

              {pending.length > 0 && (
                <div className="d-card">
                  <div className="d-card-header"><span>Pending</span><span className="d-chip">{visiblePending.length}</span></div>
                  <div className="d-task-list">
                    {visiblePending.length === 0 ? (
                      <div className="d-task-empty">No pending tasks match this filter.</div>
                    ) : visiblePending.map(t => (
                      <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={requestDelete}
                        onUpdateTask={updateTaskDetails} onToggleSub={toggleSubBlock}
                        onUndoSub={undoSubBlock} onUpdateSub={updateSubBlockTitle}
                        isDeleting={deletingIds.has(t.id)} />
                    ))}
                  </div>
                </div>
              )}

              {done.length > 0 && (
                <div className="d-card" style={{ opacity: .7 }}>
                  <div className="d-card-header"><span>Completed</span><span className="d-chip">{visibleDone.length}</span></div>
                  <div className="d-task-list">
                    {visibleDone.length === 0 ? (
                      <div className="d-task-empty">No completed tasks match this filter.</div>
                    ) : visibleDone.map(t => (
                      <TaskRow key={t.id} task={t} onToggle={toggleTask} onDelete={requestDelete}
                        onUpdateTask={updateTaskDetails} onToggleSub={toggleSubBlock}
                        onUndoSub={undoSubBlock} onUpdateSub={updateSubBlockTitle}
                        isDeleting={deletingIds.has(t.id)} />
                    ))}
                  </div>
                </div>
              )}

              {pending.length === 0 && done.length === 0 && (
                <div className="d-task-empty">No tasks yet. Hit “Add Task” to create your first one.</div>
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
                      style={{ background: 'transparent', border: 'none', borderBottom: '1px solid var(--accent)', color: 'var(--text-white)', fontSize: '20px', fontWeight: 'bold', outline: 'none', width: '100%', marginBottom: '4px' }}
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

              {/* ── Breadcrumb ── */}
              {settingsPage && (
                <div className="d-settings-breadcrumb">
                  <button className="d-settings-back" onClick={() => setSettingsPage(null)}>
                    <span style={{ fontSize: 18, lineHeight: 1 }}>‹</span>
                    <span>Settings</span>
                  </button>
                  <span className="d-settings-breadcrumb-sep">/</span>
                  <span className="d-settings-breadcrumb-current">
                    {settingsPage === 'account' && 'Account'}
                    {settingsPage === 'language' && 'Language'}
                    {settingsPage === 'notifications' && 'Notifications'}
                    {settingsPage === 'sync' && 'Sync'}
                    {settingsPage === 'privacy' && 'Privacy'}
                  </span>
                </div>
              )}

              {/* ── Category grid (when no page selected) ── */}
              {!settingsPage && (
                <>
                  <h1 className="d-h1">{t('dashboard.settings')}</h1>
                  <p className="d-sub">{t('dashboard.settingsDesc')}</p>
                  <div className="d-settings-category-grid">
                    {[
                      { id: 'account', title: t('dashboard.catAccount'), icon: <IconUser />, desc: t('dashboard.catAccountDesc') },
                      { id: 'language', title: t('dashboard.catLanguage'), icon: <IconGlobe />, desc: t('dashboard.catLanguageDesc') },
                      { id: 'notifications', title: t('dashboard.catNotifications'), icon: <IconBell />, desc: t('dashboard.catNotificationsDesc') },
                      { id: 'sync', title: t('dashboard.catSync'), icon: <IconSync />, desc: t('dashboard.catSyncDesc') },
                      { id: 'privacy', title: t('dashboard.catPrivacy'), icon: <IconShield />, desc: t('dashboard.catPrivacyDesc') },
                    ].map(section => (
                      <button key={section.id} className="d-settings-category" onClick={() => setSettingsPage(section.id)}>
                        <div className="d-settings-category-icon">{section.icon}</div>
                        <div className="d-settings-category-text">
                          <strong>{section.title}</strong>
                          <span>{section.desc}</span>
                        </div>
                        <span className="d-settings-category-arrow">›</span>
                      </button>
                    ))}
                  </div>
                </>
              )}

              {/* ── Account detail ── */}
              {settingsPage === 'account' && (
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

              {/* ── Language detail ── */}
              {settingsPage === 'language' && (
                <div className="d-card">
                  <div className="d-card-header"><span>🌐</span><span>{t('dashboard.language')}</span></div>
                  <p className="d-field-help">{t('dashboard.catLanguageDesc')}</p>
                  <div className="d-field-block">
                    <span className="d-field-label">{t('dashboard.langPrimary')}</span>
                    <p className="d-field-help">{t('dashboard.langPrimaryDesc')}</p>
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
                            borderColor: languageDraft.primary === option.code ? 'var(--accent)' : 'var(--border)',
                            background: languageDraft.primary === option.code ? 'var(--accent-dim)' : 'transparent',
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
                      <span className="d-field-label">{t('dashboard.langSecondary')}</span>
                      <p className="d-field-help">{t('dashboard.langSecondaryDesc')}</p>
                      <select className="d-input" value={languageDraft.secondary} onChange={e => setLanguageDraft({ ...languageDraft, secondary: e.target.value })}>
                        {LANGUAGE_OPTIONS.filter(option => option.code !== languageDraft.primary).map(option => <option key={option.code} value={option.code}>{option.label}</option>)}
                      </select>
                    </label>
                    <label>
                      <span className="d-field-label">{t('dashboard.langContentMode')}</span>
                      <p className="d-field-help">{t('dashboard.langContentModeDesc')}</p>
                      <select className="d-input" value={languageDraft.contentMode} onChange={e => setLanguageDraft({ ...languageDraft, contentMode: e.target.value })}>
                        <option value="auto">{t('dashboard.langAutoDetect')}</option>
                        <option value="primary">{t('dashboard.langPrimaryOnly')}</option>
                        <option value="bilingual">{t('dashboard.langBilingual')}</option>
                      </select>
                    </label>
                    <label>
                      <span className="d-field-label">{t('dashboard.langDateFormat')}</span>
                      <p className="d-field-help">{t('dashboard.langDateFormatDesc')}</p>
                      <select className="d-input" value={languageDraft.dateFormat} onChange={e => setLanguageDraft({ ...languageDraft, dateFormat: e.target.value })}>
                        <option value="locale">{t('dashboard.langLocaleDates')}</option>
                        <option value="iso">{t('dashboard.langIsoDates')}</option>
                      </select>
                    </label>
                    <label>
                      <span className="d-field-label">{t('dashboard.langNumberFormat')}</span>
                      <p className="d-field-help">{t('dashboard.langNumberFormatDesc')}</p>
                      <select className="d-input" value={languageDraft.numberFormat} onChange={e => setLanguageDraft({ ...languageDraft, numberFormat: e.target.value })}>
                        <option value="locale">{t('dashboard.langLocaleNumbers')}</option>
                        <option value="compact">{t('dashboard.langCompactNumbers')}</option>
                        <option value="plain">{t('dashboard.langPlainNumbers')}</option>
                      </select>
                    </label>
                  </div>
                  <label className="d-toggle-row"><span>{t('dashboard.langTransliterate')}</span><input type="checkbox" checked={languageDraft.transliteration} onChange={e => setLanguageDraft({ ...languageDraft, transliteration: e.target.checked })} /></label>
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="d-btn d-btn--primary" onClick={saveLanguageSettings} disabled={settingsSaving}>{settingsSaving ? t('dashboard.saving') : t('dashboard.saveLanguage')}</button>
                  </div>
                </div>
              )}

              {/* ── Notifications detail ── */}
              {settingsPage === 'notifications' && (
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
                            borderColor: notificationDraft.level === level.id ? 'var(--accent)' : 'var(--border)',
                            background: notificationDraft.level === level.id ? 'var(--accent-dim)' : 'transparent',
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

              {/* ── Sync detail (provider squares) ── */}
              {settingsPage === 'sync' && (
                <div className="d-sync-page">
                  <p className="d-field-help" style={{ marginBottom: 20 }}>Connect external services to sync tasks, events, and emails directly into your workspace.</p>
                  <div className="d-provider-grid">
                    {INTEGRATION_PROVIDERS.map(provider => {
                      const status = getIntegrationStatus(provider.id);
                      const rawConnected = status.connected;
                      const expired = status.is_expired;
                      const connectedAndGood = rawConnected && !expired;

                      // Provider-specific health checks
                      const notionMissingDb = provider.id === 'notion' && rawConnected && !status.settings?.notion_database_id;
                      const needsReconnect = (rawConnected && expired) || notionMissingDb;

                      const connected = connectedAndGood && !needsReconnect;

                      let btnLabel = 'Connect';
                      let btnAction = null;
                      if (provider.id === 'google') {
                        if (needsReconnect) { btnLabel = 'Reconnect'; btnAction = connectGoogle; }
                        else if (connected) { btnLabel = 'Disconnect'; btnAction = disconnectGoogle; }
                        else { btnLabel = 'Connect'; btnAction = connectGoogle; }
                      } else if (provider.id === 'notion') {
                        if (expired) { btnLabel = 'Reconnect'; btnAction = connectNotion; }
                        else if (notionMissingDb) { btnLabel = 'Configure'; btnAction = () => openSyncSettings('notion'); }
                        else if (connected) { btnLabel = 'Disconnect'; btnAction = disconnectNotion; }
                        else { btnLabel = 'Connect'; btnAction = connectNotion; }
                      }

                      let bg = 'var(--accent)';
                      let txt = 'var(--text-white)';
                      let bdr = 'none';
                      if (provider.id === 'notion' && expired) {
                        bg = '#ef4444'; txt = '#fff'; bdr = 'none';
                      } else if (provider.id === 'notion' && notionMissingDb) {
                        bg = '#f59e0b'; txt = '#fff'; bdr = 'none';
                      } else if (expired) {
                        bg = '#ef4444'; txt = '#fff'; bdr = 'none';
                      } else if (connected) {
                        bg = 'var(--accent-dim)'; txt = 'var(--accent)'; bdr = '1px solid var(--accent)';
                      }

                      const LOGO_SIZE = 200;
                      const logoEl = <img src={provider.logo} alt={provider.name} style={{ width: LOGO_SIZE, height: LOGO_SIZE, objectFit: 'contain' }} />;
                      const appIcons = {
                        'Tasks': <TaskListLogo size={13} />,
                        'Calendar': <CalendarLogo size={13} />,
                        'Gmail': <GmailLogo size={13} />,
                        'Databases': <NotionLogo size={13} />,
                      };
                      const available = provider.id === 'google' || provider.id === 'notion';
                      return (
                        <div key={provider.id} className="d-provider-card" style={{ position: 'relative' }}>
                          <div className="d-provider-card-header">
                            <span className="d-provider-name">{provider.name}</span>
                            {available && (
                              <button className="d-provider-cog" onClick={() => openSyncSettings(provider.id)} title="Sync settings">
                                <IconSettings />
                              </button>
                            )}
                          </div>
                          {needsReconnect && (
                            <div style={{ position: 'absolute', top: 10, right: 44, fontSize: 11, background: expired ? '#ef4444' : '#f59e0b', color: '#fff', padding: '2px 8px', borderRadius: 8, fontWeight: 600 }}>
                              {expired ? 'Expired' : 'Not configured'}
                            </div>
                          )}
                          <div className="d-provider-card-middle">
                            <div className="d-provider-logo">{logoEl}</div>
                          </div>
                          <div className="d-provider-apps">
                            {provider.apps.map(app => (
                              <span key={app} className="d-provider-app">
                                {appIcons[app] && <span style={{ marginRight: 5, display: 'inline-flex', verticalAlign: 'middle' }}>{appIcons[app]}</span>}
                                {app}
                              </span>
                            ))}
                          </div>
                          <div className="d-provider-card-footer">
                            {btnAction ? (
                              <button className="d-btn d-btn--primary" onClick={btnAction} disabled={integrationSaving === provider.id} style={{
                                width: '100%',
                                background: bg,
                                color: txt,
                                border: bdr
                              }}>
                                {integrationSaving === provider.id ? 'Working...' : btnLabel}
                              </button>
                            ) : (
                              <button className="d-btn" disabled style={{ width: '100%', opacity: 0.4, background: 'var(--surface)', color: 'var(--text3)', border: '1px solid var(--accent-dim)' }}>
                                Coming soon
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {integrationMessage && <div className="d-integration-message" style={{ marginTop: 16 }}>{integrationMessage}</div>}
                </div>
              )}

              {/* ── Privacy detail ── */}
              {settingsPage === 'privacy' && (
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
          )}
          {tab === 'settings' && false && (
            <div className="d-section fade-in">
              <h1 className="d-h1">{t('dashboard.settings')}</h1>

              {/* Language Selector */}
              <div className="d-card" style={{ marginBottom: 16 }}>
                <div className="d-card-header"><span>🌐</span><span>{t('dashboard.language')}</span></div>
                <div style={{ display: 'flex', gap: 10, padding: '12px 0 0 0' }}>
                  {[{ code: 'ar', label: 'العربية 🇸🇦' }, { code: 'en', label: 'English 🇬🇧' }].map(({ code, label }) => (
                    <button
                      key={code}
                      onClick={() => changeLanguage(code)}
                      style={{
                        flex: 1, padding: '10px', borderRadius: '10px', cursor: 'pointer',
                        border: lang === code ? '2px solid var(--accent)' : '1px solid var(--border)',
                        background: lang === code ? 'var(--accent-dim)' : 'transparent',
                        color: lang === code ? 'var(--accent)' : 'var(--text2)',
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
                        <div style={{ width: 36, height: 20, background: 'var(--accent)', borderRadius: 10, position: 'relative' }}>
                          <div style={{ position: 'absolute', right: 2, top: 2, width: 16, height: 16, background: 'var(--text-white)', borderRadius: '50%' }}></div>
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
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid var(--border)', marginBottom: '0' }}>
                <h1 className="d-h1" style={{ margin: 0, fontSize: '18px' }}>DopaPal Assistant</h1>
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {chatMessages.map((m, i) => (
                  <div key={i} style={{
                    alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                    background: m.sender === 'user' ? 'var(--accent)' : 'transparent',
                    color: 'var(--text-white)', padding: '12px 16px', borderRadius: '16px',
                    borderBottomRightRadius: m.sender === 'user' ? '4px' : '16px',
                    borderBottomLeftRadius: m.sender === 'ai' ? '4px' : '16px',
                    maxWidth: '80%', lineHeight: '1.4'
                  }}>
                    {m.sender === 'ai' ? <MarkdownRenderer content={m.text} /> : m.text}
                  </div>
                ))}
                {isTyping && (
                  <div style={{ alignSelf: 'flex-start', background: 'transparent', color: 'var(--text3)', padding: '12px 16px', borderRadius: '16px', borderBottomLeftRadius: '4px' }}>
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '20px' }}>
                      <span style={{ width: '6px', height: '6px', background: 'var(--text3)', borderRadius: '50%', animation: 'pulse 1.5s infinite' }}></span>
                      <span style={{ width: '6px', height: '6px', background: 'var(--text3)', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.2s' }}></span>
                      <span style={{ width: '6px', height: '6px', background: 'var(--text3)', borderRadius: '50%', animation: 'pulse 1.5s infinite 0.4s' }}></span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', background: 'var(--overlay)' }}>
                <div style={{ 
                  display: 'flex', 
                  gap: '8px', 
                  background: 'transparent', 
                  border: '1px solid var(--border)', 
                  borderRadius: '24px', 
                  padding: '6px 6px 6px 16px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                  alignItems: 'center',
                  transition: 'all 0.3s ease'
                }}>
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSendChat()}
                    placeholder="Message DopaPal AI..."
                    style={{ flex: 1, background: 'transparent', border: 'none', color: 'var(--text-white)', outline: 'none', fontSize: '14px' }}
                  />
                  <button 
                    onClick={handleSendChat} 
                    disabled={!chatInput.trim() || isTyping}
                    style={{ 
                      borderRadius: '50%', 
                      width: '36px', 
                      height: '36px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      background: chatInput.trim() && !isTyping ? 'var(--accent)' : 'var(--surface)', 
                      color: chatInput.trim() && !isTyping ? 'var(--text-white)' : 'var(--text3)', 
                      border: 'none', 
                      cursor: chatInput.trim() && !isTyping ? 'pointer' : 'default',
                      transition: 'all 0.2s',
                      boxShadow: chatInput.trim() && !isTyping ? '0 2px 10px var(--accent-dim)' : 'none'
                    }}
                    title="Send message"
                  >
                    <IconSend />
                  </button>
                </div>
              </div>
            </div>
          )}

          {tab === 'sync' && (
            <div className="d-section fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '10px 0' }}>
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid var(--border)', marginBottom: '0' }}>
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
                        <img src={provider.logo} alt="" className="d-integration-logo" />
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
                          <img src={provider.logo} alt="" className="d-integration-logo d-integration-logo--lg" />
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

                        {provider.id === 'google' ? (
                          <div className="d-modal-form">
                            <p className="d-field-help">Connect your Google account to sync Calendar events and scan Gmail for tasks.</p>
                            <button className="d-btn d-btn--primary" onClick={connectGoogle} disabled={!!integrationSaving} style={{ alignSelf: 'stretch' }}>
                              {integrationSaving === 'google' ? 'Connecting...' : (status.connected ? 'Reconnect Google' : 'Connect with Google')}
                            </button>
                          </div>
                        ) : (
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
                            <button className="d-btn d-btn--primary" disabled={!!integrationSaving || !integrationForm.accessToken.trim()} style={{ alignSelf: 'stretch' }}>
                              {!!integrationSaving ? 'Saving...' : `Connect ${provider.name}`}
                            </button>
                          </form>
                        )}

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
              <div className="d-section-header" style={{ padding: '0 24px 12px 24px', borderBottom: '1px solid var(--border)', marginBottom: '0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <h1 className="d-h1" style={{ margin: 0, fontSize: '18px' }}>Shop</h1>
                  <div className="d-streak" style={{ background: 'rgba(251,191,36,0.1)', color: 'var(--med)', border: '1px solid rgba(251,191,36,0.3)', padding: '4px 12px', borderRadius: '16px' }}>
                    <IconSparkle /> <span style={{ fontWeight: 600 }}>{userXp} XP</span>
                  </div>
                </div>
              </div>

              {purchaseError && (
                <div style={{ margin: '16px 24px 0 24px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: 'var(--error)', borderRadius: '8px', textAlign: 'center', fontSize: '14px', fontWeight: 500 }}>
                  {purchaseError}
                </div>
              )}

              <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {THEMES.map(t => {
                  const isUnlocked = unlockedThemes.includes(t.id);
                  const isActive = activeTheme === t.id;
                  return (
                    <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: 'var(--surface2)', borderRadius: '12px', border: isActive ? `2px solid ${t.accent}` : '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: `linear-gradient(135deg, ${t.accent}, ${t.dim})`, border: '2px solid var(--border)' }}></div>
                        <div>
                          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-white)' }}>{t.name}</div>
                          {!isUnlocked && (
                            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)', color: 'var(--med)', padding: '4px 8px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, marginTop: '6px' }}>
                              <IconSparkle size={12} /> {t.cost} XP
                            </div>
                          )}
                          {isUnlocked && <div style={{ fontSize: '13px', color: 'var(--success)', marginTop: '6px', fontWeight: 500 }}>✓ Unlocked</div>}
                        </div>
                      </div>
                      <div>
                        {isActive ? (
                          <button className="d-btn d-btn--secondary" disabled style={{ background: 'transparent', border: `1px solid ${t.accent}`, color: t.accent }}>Equipped</button>
                        ) : isUnlocked ? (
                          <button className="d-btn" onClick={() => equipTheme(t.id)} style={{ background: t.accent }}>Equip</button>
                        ) : (
                          <button className="d-btn" onClick={() => buyTheme(t.id, t.cost)} style={{ background: 'var(--med)', color: 'var(--bg)' }}>
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
                    <div key={item.id} className="d-shop-item" style={{ borderColor: isActive ? item.accent : 'var(--border)' }}>
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
                          <button className="d-btn" onClick={() => equipShopItem(item)} style={{ background: item.accent, color: item.accent === '#fbbf24' ? 'var(--bg)' : 'var(--text-white)' }}>Use</button>
                        ) : (
                          <button className="d-btn" onClick={() => buyShopItem(item.id, item.cost)} style={{ background: 'var(--med)', color: 'var(--bg)' }}>
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

      {/* ══ DELETE CONFIRMATION ══ */}
      {confirmDeleteId != null && (
        <div className="d-modal-overlay fade-in" onClick={() => setConfirmDeleteId(null)}>
          <div className="d-confirm" onClick={e => e.stopPropagation()}>
            <div className="d-confirm-icon"><IconTrash /></div>
            <h2 className="d-confirm-title">Delete this task?</h2>
            <p className="d-confirm-text">
              {(() => {
                const tk = tasks.find(t => t.id === confirmDeleteId);
                return tk ? `“${tk.title}” and its steps will be removed. This can't be undone.`
                  : "This task and its steps will be removed. This can't be undone.";
              })()}
            </p>
            <div className="d-confirm-actions">
              <button className="d-btn d-btn--secondary" onClick={() => setConfirmDeleteId(null)}>Cancel</button>
              <button className="d-btn d-confirm-delete" onClick={performDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* ══ TOASTS (background add / update / delete feedback) ══ */}
      {toasts.length > 0 && (
        <div className="d-toast-stack">
          {toasts.map(toast => (
            <div key={toast.id} className={`d-toast d-toast--${toast.kind}`}>
              {toast.kind === 'loading' && <span className="d-toast-spinner" />}
              {toast.kind === 'success' && <span className="d-toast-mark"><IconCheck /></span>}
              <span>{toast.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* ══ ADD TASK MODAL ══ */}
      {showAddTaskModal && (
        <div className="d-modal-overlay fade-in" onClick={() => { setShowAddTaskModal(false); setIsVoiceTask(false); }}>
          <div className="d-modal-content" onClick={e => e.stopPropagation()}>
            <div className="d-modal-header">
              <h2 className="d-h1">{addTaskView === 'options' ? t('bubble.newTask') : (addTaskView === 'manual' ? t('bubble.manualEntry') : t('bubble.aiSmartInput'))}</h2>
              <button className="d-modal-close" onClick={() => { setShowAddTaskModal(false); setIsVoiceTask(false); }}>
                <IconClose />
              </button>
            </div>

            {addTaskView === 'options' && (
              <div className="d-modal-options">
                <button className="d-modal-btn" onClick={() => setAddTaskView('ai')}>
                  <div className="d-modal-icon" style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}><IconSparkle /></div>
                  <div className="d-modal-text">
                    <strong>{t('bubble.aiSmartInput')}</strong>
                    <span>{t('bubble.aiSmartInputDesc')}</span>
                  </div>
                </button>
                <button className="d-modal-btn" onClick={isRecording ? stopRecording : startRecording}>
                  <div className="d-modal-icon" style={{ background: isRecording ? 'rgba(239,68,68,.15)' : 'rgba(56,189,248,.15)', color: isRecording ? 'var(--error)' : '#38bdf8' }}>
                    {isRecording ? <div className="b-dot" style={{ background: 'var(--error)', width: 12, height: 12, borderRadius: '50%' }} /> : <IconMic />}
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
                <input className="d-input" placeholder={t('bubble.taskPlaceholder')} value={taskData.title} onChange={e => setTaskData({ ...taskData, title: e.target.value })} autoFocus />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    className="d-input"
                    placeholder={t('bubble.durationPlaceholder')}
                    value={taskData.duration}
                    onChange={e => setTaskData({ ...taskData, duration: e.target.value })}
                    style={{ flex: 1 }}
                  />
                  <button
                    onClick={() => setTaskData({ ...taskData, duration: '30m' })}
                    style={{
                      padding: '8px 16px',
                      background: 'var(--accent)',
                      color: 'var(--text-white)',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      alignSelf: 'stretch'
                    }}
                  >
                    30m
                  </button>
                  <button
                    onClick={() => setTaskData({ ...taskData, duration: '1h' })}
                    style={{
                      padding: '8px 16px',
                      background: 'var(--accent)',
                      color: 'var(--text-white)',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      alignSelf: 'stretch'
                    }}
                  >
                    1h
                  </button>
                  <button
                    onClick={() => setTaskData({ ...taskData, duration: '2h' })}
                    style={{
                      padding: '8px 16px',
                      background: 'var(--accent)',
                      color: 'var(--text-white)',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      alignSelf: 'stretch'
                    }}
                  >
                    2h
                  </button>
                </div>
                <input className="d-input" placeholder={t('bubble.dueDatePlaceholder')} value={taskData.due} onChange={e => setTaskData({ ...taskData, due: e.target.value })} />
                <textarea className="d-input" placeholder={t('bubble.notesPlaceholder')} value={taskData.notes} onChange={e => setTaskData({ ...taskData, notes: e.target.value })} />
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

      {/* ── Sync settings modal ── */}
      {(syncSettingsModal || syncSettingsClosing) && (
        <div className={`d-modal-overlay${syncSettingsClosing ? ' closing' : ''}`} onClick={closeSyncSettings}>
          <div className={`d-modal-content${syncSettingsClosing ? ' closing' : ''}`} onClick={e => e.stopPropagation()} style={{ maxWidth: syncSettingsModal === 'notion' ? 500 : 540, maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
            <div className="d-modal-header">
              <span style={{ fontWeight: 600, fontSize: 16 }}>
                {syncSettingsModal === 'notion' ? 'Notion Sync Settings' : 'Google Sync Settings'}
              </span>
              <button className="d-modal-close" onClick={closeSyncSettings}>×</button>
            </div>
            <div className="d-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 0, padding: 0, overflowY: 'auto', flex: 1 }}>
              {syncSettingsLoading ? (
                <div style={{ padding: '40px 24px', color: 'var(--text2)', textAlign: 'center' }}>Loading...</div>
              ) : syncSettingsModal === 'notion' ? (
                (() => {
                  const set = (path, val) => {
                    setSyncSettingsDraft(prev => {
                      const copy = JSON.parse(JSON.stringify(prev));
                      const parts = path.split('.');
                      let cur = copy;
                      for (let i = 0; i < parts.length - 1; i++) {
                        if (!cur[parts[i]]) cur[parts[i]] = {};
                        cur = cur[parts[i]];
                      }
                      cur[parts[parts.length - 1]] = val;
                      return copy;
                    });
                  };
                  const d = syncSettingsDraft;
                  return (
                    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                      <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        <span className="d-field-label">Database</span>
                        <p className="d-field-help" style={{ margin: 0 }}>Select which Notion database to sync tasks from.</p>
                        {notionDatabasesLoading ? (
                          <div style={{ color: 'var(--text2)', fontSize: 13, padding: '8px 0' }}>Loading databases...</div>
                        ) : availableDatabases.length > 0 ? (
                          <select
                            className="d-input"
                            style={{ appearance: 'auto' }}
                            value={d.notion_database_id || ''}
                            onChange={async e => {
                              const dbId = e.target.value;
                              set('notion_database_id', dbId);
                              if (dbId) {
                                const picked = availableDatabases.find(db => db.id === dbId);
                                if (picked) pushToast(`Selected: ${picked.title}`, 'success');
                                setNotionSchemaLoading(true);
                                try {
                                  const res = await api.get(`/sync/notion/database-schema?database_id=${dbId}`);
                                  setNotionSchema(res.properties || []);
                                } catch (err) {
                                  console.warn('Could not fetch schema', err);
                                  setNotionSchema(null);
                                } finally {
                                  setNotionSchemaLoading(false);
                                }
                              } else {
                                setNotionSchema(null);
                              }
                            }}
                          >
                            <option value="">— Pick a database —</option>
                            {availableDatabases.map(db => (
                              <option key={db.id} value={db.id}>{db.title}</option>
                            ))}
                          </select>
                        ) : d.notion_database_id ? (
                          <input className="d-input" value={d.notion_database_id} readOnly style={{ background: 'var(--bg-dim)', cursor: 'not-allowed' }} />
                        ) : (
                          <p style={{ fontSize: 13, color: 'var(--text-warning)' }}>No databases found. Make sure you've shared them with your integration in Notion.</p>
                        )}
                      </label>

                      {notionSchemaLoading ? (
                        <div style={{ padding: '16px 0', color: 'var(--text2)', fontSize: 13 }}>Loading column schema...</div>
                      ) : notionSchema && notionSchema.length > 0 ? (
                        <>
                          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
                            <span className="d-field-label" style={{ display: 'block', marginBottom: 8 }}>Property Mapping</span>
                            <p className="d-field-help" style={{ margin: '0 0 12px 0' }}>Map your Notion column names to dopaPal task fields.</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                              <SchemaSelect
                                label="Title column"
                                schema={notionSchema}
                                types={['title']}
                                value={(d.property_mapping || {}).title || ''}
                                onChange={v => set('property_mapping.title', v)}
                                placeholder="Pick title column"
                              />
                              <SchemaSelect
                                label="Deadline column"
                                schema={notionSchema}
                                types={['date']}
                                value={(d.property_mapping || {}).deadline || ''}
                                onChange={v => set('property_mapping.deadline', v)}
                                placeholder="Pick date column"
                              />
                              <SchemaSelect
                                label="Interest tag column"
                                schema={notionSchema}
                                types={['select', 'status', 'multi_select']}
                                value={(d.property_mapping || {}).interest_tag || ''}
                                onChange={v => set('property_mapping.interest_tag', v)}
                                placeholder="Pick tag column"
                                help="Select, status, or multi-select property."
                              />
                            </div>
                          </div>

                          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
                            <span className="d-field-label" style={{ display: 'block', marginBottom: 8 }}>Completion Status</span>
                            <p className="d-field-help" style={{ margin: '0 0 12px 0' }}>Select which column tracks completion and what value means "done".</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                              <SchemaSelect
                                label="Status column"
                                schema={notionSchema}
                                types={['status', 'select', 'checkbox']}
                                value={d.status_field || ''}
                                onChange={v => set('status_field', v)}
                                placeholder="Pick status column (optional)"
                                help="If set, only this column is checked for completion."
                              />
                              {(() => {
                                const statusFieldSchema = d.status_field
                                  ? notionSchema.find(p => p.name === d.status_field)
                                  : null;
                                const statusType = statusFieldSchema?.type;
                                const options = statusFieldSchema?.options;
                                if (statusType === 'checkbox') {
                                  return (
                                    <p style={{ fontSize: 13, color: 'var(--text2)', margin: 0 }}>
                                      When this checkbox is checked, the page is marked done.
                                    </p>
                                  );
                                }
                                return (
                                  <>
                                    <label className="d-toggle-row" style={{ marginBottom: 0 }}>
                                      <span style={{ fontSize: 13 }}>Skip completed pages</span>
                                      <input type="checkbox" checked={(d.sync_filters || {}).ignore_completed !== false} onChange={e => set('sync_filters.ignore_completed', e.target.checked)} />
                                    </label>
                                    <label style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                      <span style={{ fontSize: 13, color: 'var(--text2)' }}>Completed value</span>
                                      {options && options.length > 0 ? (
                                        <select
                                          className="d-input"
                                          style={{ appearance: 'auto', width: 200 }}
                                          value={(d.sync_filters || {}).completed_status_value || 'Done'}
                                          onChange={e => set('sync_filters.completed_status_value', e.target.value)}
                                        >
                                          <option value="">— Pick value —</option>
                                          {options.map(opt => (
                                            <option key={opt.name} value={opt.name}>{opt.name}</option>
                                          ))}
                                        </select>
                                      ) : (
                                        <input className="d-input" value={(d.sync_filters || {}).completed_status_value || 'Done'} onChange={e => set('sync_filters.completed_status_value', e.target.value)} placeholder="Done" style={{ width: 180 }} />
                                      )}
                                    </label>
                                  </>
                                );
                              })()}
                            </div>
                          </div>
                        </>
                      ) : d.notion_database_id && !notionSchemaLoading ? (
                        <p style={{ fontSize: 13, color: 'var(--text-warning)', padding: '8px 0' }}>Could not load database schema. Make sure the integration has access to the database.</p>
                      ) : null}
                    </div>
                  );
                })()
              ) : (
                (() => {
                  const set = (path, val) => {
                    setSyncSettingsDraft(prev => {
                      const copy = JSON.parse(JSON.stringify(prev));
                      const parts = path.split('.');
                      let cur = copy;
                      for (let i = 0; i < parts.length - 1; i++) {
                        if (!cur[parts[i]]) cur[parts[i]] = {};
                        cur = cur[parts[i]];
                      }
                      cur[parts[parts.length - 1]] = val;
                      return copy;
                    });
                  };
                  const d = syncSettingsDraft;
                  const parseChips = (str) => (str || '').split(/[,;]+/).map(s => s.trim().toLowerCase()).filter(Boolean);
                  const chipsToStr = (arr) => arr.join(', ');

                  return ['tasks', 'calendar', 'gmail'].map((app, idx) => {
                    const appDraft = d[app] || {};
                    const appIconsMap = { tasks: <TaskListLogo size={16} />, calendar: <CalendarLogo size={16} />, gmail: <GmailLogo size={16} /> };
                    return (
                      <div key={app} style={{ borderBottom: idx < 2 ? '1px solid var(--border)' : 'none', padding: '20px 24px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                          <span style={{ display: 'inline-flex' }}>{appIconsMap[app]}</span>
                          <span style={{ fontWeight: 600, fontSize: 14 }}>{app.charAt(0).toUpperCase() + app.slice(1)}</span>
                          <label className="d-toggle-row" style={{ marginLeft: 'auto', marginBottom: 0, gap: 8 }}>
                            <span style={{ fontSize: 12, color: 'var(--text2)' }}>{appDraft.enabled !== false ? 'On' : 'Off'}</span>
                            <input type="checkbox" checked={appDraft.enabled !== false} onChange={e => set(`${app}.enabled`, e.target.checked)} />
                          </label>
                        </div>

                        {app === 'tasks' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <label className="d-toggle-row" style={{ marginBottom: 0 }}>
                              <span style={{ fontSize: 13 }}>Include completed tasks</span>
                              <input type="checkbox" checked={!!appDraft.include_completed} onChange={e => set('tasks.include_completed', e.target.checked)} />
                            </label>
                            <label className="d-toggle-row" style={{ marginBottom: 0 }}>
                              <span style={{ fontSize: 13 }}>Include tasks without a due date</span>
                              <input type="checkbox" checked={appDraft.include_no_due_date !== false} onChange={e => set('tasks.include_no_due_date', e.target.checked)} />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Task category tags</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Tasks from Google will be tagged with these labels.</p>
                              <ChipInput values={parseChips(appDraft.interest_tag)} onChange={vals => set('tasks.interest_tag', chipsToStr(vals))} placeholder="Type tag and press Enter" />
                            </label>
                          </div>
                        )}

                        {app === 'calendar' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Include keywords</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Events with these words will be imported.</p>
                              <ChipInput values={parseChips(appDraft.include_keywords)} onChange={vals => set('calendar.include_keywords', chipsToStr(vals))} placeholder="Type and press Enter" />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Exclude keywords</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Events with these words in the title will be skipped.</p>
                              <ChipInput values={parseChips(appDraft.exclude_keywords)} onChange={vals => set('calendar.exclude_keywords', chipsToStr(vals))} placeholder="Type and press Enter" />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Minimum duration</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Events shorter than this (minutes) are treated as meetings.</p>
                              <input className="d-input" type="number" min={0} value={appDraft.min_duration_minutes ?? 30} onChange={e => set('calendar.min_duration_minutes', parseInt(e.target.value) || 0)} style={{ width: 100 }} />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Event types to include</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Allowed: default, focusTime, outOfOffice, workingLocation.</p>
                              <ChipInput values={parseChips(appDraft.include_event_types || 'default')} onChange={vals => set('calendar.include_event_types', chipsToStr(vals) || 'default')} placeholder="Type and press Enter" />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Event category tags</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Events from Google Calendar will be tagged with these labels.</p>
                              <ChipInput values={parseChips(appDraft.interest_tag)} onChange={vals => set('calendar.interest_tag', chipsToStr(vals))} placeholder="Type tag and press Enter" />
                            </label>
                          </div>
                        )}

                        {app === 'gmail' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Include keywords</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Emails with these words in the subject or body will be imported.</p>
                              <ChipInput values={parseChips(appDraft.include_keywords)} onChange={vals => set('gmail.include_keywords', chipsToStr(vals))} placeholder="Type and press Enter" />
                            </label>
                            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              <span className="d-field-label">Include senders</span>
                              <p className="d-field-help" style={{ margin: 0 }}>Only import emails from these addresses.</p>
                              <ChipInput values={parseChips(appDraft.include_senders)} onChange={vals => set('gmail.include_senders', chipsToStr(vals))} placeholder="Type and press Enter" />
                            </label>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()
              )}
            </div>
            <div className="d-modal-footer">
              <button className="d-btn" onClick={closeSyncSettings}>Cancel</button>
              <button className="d-btn d-btn--primary" onClick={saveSyncSettings} disabled={syncSettingsSaving} style={{ background: 'var(--accent)', color: 'var(--text-white)', border: 'none' }}>
                {syncSettingsSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
