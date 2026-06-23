export const THEMES = [
  { id: 'default', name: 'Dopa Default', cost: 0, accent: '#a78bfa', 'accent-rgb': '167,139,250', glow: 'rgba(167,139,250,.35)', dim: 'rgba(167,139,250,.12)', bg: '#080810', 'bg-rgb': '8,8,16', surface: 'rgba(16,15,30,.6)', 'surface-rgb': '16,15,30', surface2: 'rgba(24,22,42,.6)', 'surface-alt': '#12102a', 'surface-alt2': '#1c1640', border: 'rgba(167,139,250,.2)', text: '#f0eeff', text2: '#9b96c9', text3: '#5a567a', 'text3-rgb': '90,86,122', high: '#f87171', 'high-rgb': '248,113,113', med: '#fbbf24', low: '#34d399', 'low-rgb': '52,211,153', error: '#ef4444', 'error-rgb': '239,68,68', overlay: 'rgba(0,0,0,.55)', 'glass-rgb': '255,255,255' },
  { id: 'ocean', name: 'Ocean Breeze', cost: 500, accent: '#38bdf8', 'accent-rgb': '56,189,248', glow: 'rgba(56,189,248,.35)', dim: 'rgba(56,189,248,.12)', bg: '#0b1622', 'bg-rgb': '11,22,34', surface: 'rgba(11,30,50,.6)', 'surface-rgb': '11,30,50', surface2: 'rgba(15,40,65,.6)', 'surface-alt': '#0c1a30', 'surface-alt2': '#122840', border: 'rgba(56,189,248,.2)', text: '#e0f2fe', text2: '#7dd3fc', text3: '#3b82f6', 'text3-rgb': '59,130,246', high: '#f87171', 'high-rgb': '248,113,113', med: '#fbbf24', low: '#2dd4bf', 'low-rgb': '45,212,191', error: '#ef4444', 'error-rgb': '239,68,68', overlay: 'rgba(0,0,0,.55)', 'glass-rgb': '255,255,255' },
  { id: 'sunset', name: 'Sunset Flare', cost: 1500, accent: '#f97316', 'accent-rgb': '249,115,22', glow: 'rgba(249,115,22,.35)', dim: 'rgba(249,115,22,.12)', bg: '#1c0f08', 'bg-rgb': '28,15,8', surface: 'rgba(30,18,12,.6)', 'surface-rgb': '30,18,12', surface2: 'rgba(40,22,15,.6)', 'surface-alt': '#1e1008', 'surface-alt2': '#281a0e', border: 'rgba(249,115,22,.2)', text: '#fff7ed', text2: '#fdba74', text3: '#c2410c', 'text3-rgb': '194,65,12', high: '#ef4444', 'high-rgb': '239,68,68', med: '#fbbf24', low: '#34d399', 'low-rgb': '52,211,153', error: '#ef4444', 'error-rgb': '239,68,68', overlay: 'rgba(0,0,0,.55)', 'glass-rgb': '255,255,255' },
  { id: 'cyber', name: 'Neon Cyberpunk', cost: 3000, accent: '#ec4899', 'accent-rgb': '236,72,153', glow: 'rgba(236,72,153,.35)', dim: 'rgba(236,72,153,.12)', bg: '#0a0014', 'bg-rgb': '10,0,20', surface: 'rgba(20,5,35,.6)', 'surface-rgb': '20,5,35', surface2: 'rgba(30,10,50,.6)', 'surface-alt': '#12001e', 'surface-alt2': '#200030', border: 'rgba(236,72,153,.2)', text: '#fdf4ff', text2: '#f0abfc', text3: '#a21caf', 'text3-rgb': '162,28,175', high: '#fb7185', 'high-rgb': '251,113,133', med: '#fbbf24', low: '#2dd4bf', 'low-rgb': '45,212,191', error: '#ef4444', 'error-rgb': '239,68,68', overlay: 'rgba(0,0,0,.55)', 'glass-rgb': '255,255,255' },
  { id: 'gold', name: 'Midnight Gold', cost: 10000, accent: '#fbbf24', 'accent-rgb': '251,191,36', glow: 'rgba(251,191,36,.35)', dim: 'rgba(251,191,36,.12)', bg: '#0d0a02', 'bg-rgb': '13,10,2', surface: 'rgba(30,22,8,.6)', 'surface-rgb': '30,22,8', surface2: 'rgba(40,30,12,.6)', 'surface-alt': '#140e04', 'surface-alt2': '#1c1806', border: 'rgba(251,191,36,.2)', text: '#fefce8', text2: '#fde68a', text3: '#a16207', 'text3-rgb': '161,98,7', high: '#f87171', 'high-rgb': '248,113,113', med: '#fbbf24', low: '#34d399', 'low-rgb': '52,211,153', error: '#ef4444', 'error-rgb': '239,68,68', overlay: 'rgba(0,0,0,.55)', 'glass-rgb': '255,255,255' },
];

export const THEME_VARS = [
  'accent', 'accent-rgb', 'accent-glow', 'accent-dim',
  'bg', 'bg-rgb', 'surface', 'surface-rgb', 'surface2', 'surface-alt', 'surface-alt2',
  'border', 'text', 'text2', 'text3', 'text3-rgb',
  'high', 'high-rgb', 'med', 'low', 'low-rgb',
  'error', 'error-rgb', 'overlay', 'glass-rgb',
];

export function applyTheme(themeId) {
  const theme = THEMES.find(t => t.id === themeId) || THEMES[0];
  for (const v of THEME_VARS) {
    document.documentElement.style.setProperty(`--${v}`, theme[v]);
  }
}

export function getActiveThemeId() {
  try {
    return localStorage.getItem('dopapal_active_theme_v3') || 'default';
  } catch {
    return 'default';
  }
}
