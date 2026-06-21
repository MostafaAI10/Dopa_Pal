import React, { useState, useRef, useCallback, useEffect } from 'react';
import './Bubble.css';
import api from '../../services/api';
import { useLanguage } from '../../contexts/LanguageContext';
import { api as serverApi } from '../../services/api';

/* ─── Detect Electron ───────────────────────────────────── */
const IS_ELECTRON = typeof window !== 'undefined' && !!window.electronAPI;

/* ─── Window sizes per view ─────────────────────────────── */
const SIZES = {
  icon      : [80,  80],
  panel     : [480, 360],
  addMenu   : [360, 550],
  voice     : [360, 550],
  aiSummary : [360, 550],
  aiSummaryDisplay: [360, 550],
  manual    : [360, 650],
};

const ORB_SIZE        = 68;
const ROOT_PAD_BOTTOM = 6;
const DRAG_PX         = 5;

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

/* ─── Priority auto-calc from due date ──────────────────── */
function calcPriority(dueDateStr) {
  if (!dueDateStr) return 'low';
  const diff = (new Date(dueDateStr) - new Date()) / (1000 * 60 * 60 * 24);
  if (diff < 0)   return 'overdue';
  if (diff < 1)   return 'urgent';
  if (diff < 3)   return 'high';
  if (diff < 7)   return 'medium';
  return 'low';
}

const PRIORITY_META = {
  overdue : { label: 'OVERDUE', color: '#ef4444' },
  urgent  : { label: 'URGENT',  color: '#f97316' },
  high    : { label: 'HIGH',    color: '#f59e0b' },
  medium  : { label: 'MEDIUM',  color: '#eab308' },
  low     : { label: 'LOW',     color: '#34d399' },
};

/* ─── SVG Icons ─────────────────────────────────────────── */
const Svg = ({ size = 22, children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {children}
  </svg>
);

const BrainIcon  = () => <span style={{ fontSize: '36px', filter: 'drop-shadow(0 0 10px rgba(236,72,153,.6))', transform: 'translateY(-2px)' }}>🧠</span>;
const HomeIcon    = () => <Svg><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></Svg>;
const PlusIcon    = () => <Svg><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></Svg>;
const SparkleIcon = () => <Svg><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5z"/></Svg>;
const MicIcon     = () => <Svg><rect x="9" y="3" width="6" height="10" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></Svg>;
const PenIcon     = () => <Svg><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/></Svg>;
const ClipboardIcon=() => <Svg><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></Svg>;
const CloseIcon   = () => <Svg size={11}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></Svg>;
const BackIcon    = () => <Svg size={16}><polyline points="15 18 9 12 15 6"/></Svg>;
const SendIcon    = () => <Svg><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></Svg>;

/* ─── Main Bubble ───────────────────────────────────────── */
export default function Bubble() {
  const { t } = useLanguage();
  const [view,       setView]      = useState('icon'); // icon|panel|addMenu|voice|aiSummary|manual
  const [panelAnim,  setPanelAnim] = useState('');
  const [panelSide,  setPanelSide] = useState('left');
  const [recording,  setRecording] = useState(false);
  const [isLoading,  setIsLoading] = useState(false);
  const [aiText,     setAiText]    = useState('');
  const [summaryData, setSummaryData] = useState(null);
  const [task, setTask] = useState({ title:'', duration:'', due:'', notes:'' });

  const mediaRecorder = useRef(null);
  const audioChunks   = useRef([]);

  const drag    = useRef({ on:false, sx:0, sy:0, lx:0, ly:0, moved:false });
  const exitTmr = useRef(null);

  /* ── Resize helper ──────────────────────────────────── */
  const resize = useCallback((viewName) => {
    // Resize is no longer needed since we use a fixed size window and click-through
  }, []);

  /* ── Navigate between views ─────────────────────────── */
  const goTo = useCallback((nextView, anim = 'in') => {
    clearTimeout(exitTmr.current);
    if (nextView === 'icon') {
      setPanelAnim('out');
      exitTmr.current = setTimeout(() => {
        setView('icon');
      }, 160);
    } else {
      setView(nextView);
      setPanelAnim(anim);
    }
  }, []);

  useEffect(() => {
    if (IS_ELECTRON && window.electronAPI.onOpenAddMenu) {
      window.electronAPI.onOpenAddMenu(() => {
        goTo('addMenu');
      });
    }
    return () => clearTimeout(exitTmr.current);
  }, [goTo]);

  /* ── Click-through logic ───────────────────────────── */
  useEffect(() => {
    if (!IS_ELECTRON) return;
    const handleMouseMove = (e) => {
      // If mouse is directly over the body, root, or transparent SVG, pass clicks through!
      const target = e.target;
      const isTransparent = 
        target === document.body || 
        target === document.documentElement || 
        target.classList.contains('b-root');
      
      window.electronAPI.setIgnoreMouse(isTransparent);
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  /* ── Drag (screenX for smooth motion) ───────────────── */
  const onOrbMouseDown = useCallback((e) => {
    if (e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();
    drag.current = { on:true, sx:e.screenX, sy:e.screenY,
                     lx:e.screenX, ly:e.screenY, moved:false };

    const onMove = (mv) => {
      const d = drag.current;
      if (!d.on) return;
      const dx = mv.screenX - d.lx;
      const dy = mv.screenY - d.ly;
      if (!d.moved && Math.hypot(mv.screenX-d.sx, mv.screenY-d.sy) > DRAG_PX) d.moved = true;
      if (d.moved && IS_ELECTRON) window.electronAPI.moveWindow(dx, dy);
      d.lx = mv.screenX; d.ly = mv.screenY;
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup',   onUp);
      if (!drag.current.moved) {
        if (view === 'icon') {
          // If orb is on the right half of the screen, show panel on its left
          setPanelSide(window.screenX > (window.screen.width / 2) ? 'left' : 'right');
          goTo('panel');
        } else {
          goTo('icon');
        }
      }
      drag.current.on = false;
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',   onUp);
  }, [view, goTo]);

  /* ── Task submit ─────────────────────────────────────── */
  const submitTask = useCallback(async (source, extraData = null) => {
    setIsLoading(true);
    try {
      if (source === 'manual') {
        // Use the server's duration parser for consistent parsing
        let hours = 2.0;
        
        if (task.duration && task.duration.trim()) {
          try {
            // Call the server's duration parser API
            const response = await fetch('/api/v1/parse-duration', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ duration: task.duration })
            });
            
            if (response.ok) {
              const result = await response.json();
              hours = result.hours;
            } else {
              // Fallback to client-side parsing if server API fails
              hours = parseDuration(task.duration);
            }
          } catch (error) {
            console.error("Failed to parse duration:", error);
            // Fallback to client-side parsing
            hours = parseDuration(task.duration);
          }
        }

        await window.electronAPI.createTask({
          title: task.title,
          deadline: task.due ? new Date(task.due).toISOString() : new Date(Date.now() + 86400000 * 7).toISOString(),
          estimatedHours: hours,
          sourceType: 'manual',
          interestTag: null
        });
      } else if (source === 'ai') {
        await window.electronAPI.ingestTask({
          source_text: aiText,
          source_type: 'highlight'
        });
      } else if (source === 'voice' && extraData) {
        const arrayBuffer = await extraData.arrayBuffer();
        await window.electronAPI.ingestVoiceTask(arrayBuffer);
      }
      
      // Reset forms
      setTask({ title:'', duration:'', due:'', notes:'' });
      setAiText('');
      goTo('icon');
    } catch (e) {
      console.error("Failed to submit task:", e);
      alert("Error saving task: " + e.message);
    } finally {
      setIsLoading(false);
    }
  }, [task, aiText, goTo]);

  const handleAISummaryClick = async () => {
    goTo('aiSummaryDisplay');
    setIsLoading(true);
    setSummaryData(null);
    try {
      const res = await api.getAISummary();
      setSummaryData(res);
    } catch (e) {
      console.error("Failed to get summary:", e);
      setSummaryData({ text: "عذراً، حدث خطأ أثناء الاتصال بالـ AI." });
    } finally {
      setIsLoading(false);
    }
  };

  /* ── Voice Recording Logic ───────────────────────────── */
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunks.current = [];
      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };
      mediaRecorder.current.start();
      setRecording(true);
    } catch (e) {
      console.error("Microphone error:", e);
      alert("Could not access microphone.");
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder.current) return;
    mediaRecorder.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
      await submitTask('voice', audioBlob);
      mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
    };
    mediaRecorder.current.stop();
    setRecording(false);
  };

  /* ── Priority from due date ──────────────────────────── */
  const priority    = calcPriority(task.due);
  const priorityMeta = PRIORITY_META[priority];

  /* ── Render ──────────────────────────────────────────── */
  return (
    <div className="b-root">

      {/* ━━━━━━━━ MAIN PANEL ━━━━━━━━ */}
      {(view === 'panel') && (
        <div className={`b-panel b-panel--vertical b-panel--${panelSide}-of-orb b-panel--${panelAnim}`}>
          <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

          <button className="b-action" id="btn-home" onClick={() => {
            goTo('icon');
            if (IS_ELECTRON) window.electronAPI.openDashboard();
          }}>
            <HomeIcon /><span>Home</span>
          </button>

          <div className="b-sep" />

          <button className="b-action" id="btn-add-task" onClick={() => goTo('addMenu')}>
            <PlusIcon /><span>Add Task</span>
          </button>

          <div className="b-sep" />

          <button className="b-action b-action--ai" id="btn-ai" onClick={handleAISummaryClick}>
            <span className="b-ai-icon"><SparkleIcon /><i className="b-dot" /></span>
            <span>AI Summary</span>
          </button>
        </div>
      )}

      {/* ━━━━━━━━ ADD TASK MENU ━━━━━━━━ */}
      {view === 'addMenu' && (
        <div className={`b-panel b-panel--tall b-panel--${panelAnim}`}>
          <button className="b-back" onClick={() => goTo('panel')}><BackIcon /></button>
          <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

          <div className="b-menu-title">Add a Task</div>
          <div className="b-menu-sub">How do you want to capture it?</div>

          <div className="b-menu-options">
            {/* Voice */}
            <button className="b-menu-btn" id="btn-voice" onClick={() => goTo('voice')}>
              <div className="b-menu-icon b-menu-icon--purple"><MicIcon /></div>
              <div className="b-menu-text">
                <span className="b-menu-label">{t('bubble.voiceMemo')}</span>
                <span className="b-menu-desc">{t('bubble.voiceMemoDesc')}</span>
              </div>
            </button>

            {/* AI Smart Input */}
            <button className="b-menu-btn" id="btn-ai-summary" onClick={() => goTo('aiSummary')}>
              <div className="b-menu-icon b-menu-icon--blue"><PenIcon /></div>
              <div className="b-menu-text">
                <span className="b-menu-label">{t('bubble.aiSmartInput')}</span>
                <span className="b-menu-desc">{t('bubble.aiSmartInputDesc')}</span>
              </div>
            </button>

            {/* Manual */}
            <button className="b-menu-btn b-menu-btn--primary" id="btn-manual" onClick={() => goTo('manual')}>
              <div className="b-menu-icon b-menu-icon--green"><ClipboardIcon /></div>
              <div className="b-menu-text">
                <span className="b-menu-label">{t('bubble.manualEntry')}</span>
                <span className="b-menu-desc">{t('bubble.manualEntryDesc')}</span>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* ━━━━━━━━ VOICE VIEW ━━━━━━━━ */}
      {view === 'voice' && (
        <div className={`b-panel b-panel--tall b-panel--${panelAnim}`} style={{ flexDirection:'column', gap:14 }}>
          <button className="b-back" onClick={() => goTo('addMenu')}><BackIcon /></button>
          <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

          <div className="b-menu-title">Voice Input</div>
          <div className="b-menu-sub">Press &amp; hold to record</div>

          <button
            className={`b-voice-btn ${recording ? 'b-voice-btn--active' : ''}`}
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            disabled={isLoading}
          >
            <MicIcon />
            {isLoading ? <span>Processing AI...</span> : (recording ? <span>Recording…</span> : <span>Hold to speak</span>)}
          </button>
        </div>
      )}

      {/* ━━━━━━━━ AI SUMMARY DISPLAY ━━━━━━━━ */}
       {view === 'aiSummaryDisplay' && (
         <div className={`b-panel b-panel--tall b-panel--${panelAnim}`} style={{ flexDirection:'column', gap:12 }}>
           <button className="b-back" onClick={() => goTo('panel')}><BackIcon /></button>
           <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

           <div className="b-menu-title" style={{ display:'flex', alignItems:'center', gap:'8px' }}>
              <SparkleIcon /> AI Summary
           </div>
           
           <div style={{ flex: 1, overflowY: 'auto', padding: '10px 0', color: 'var(--text2)', fontSize: '14px', lineHeight: '1.6' }}>
              {isLoading ? (
                <div style={{ display:'flex', justifyContent:'center', padding:'20px' }}>
                  <div style={{ animation:'pulse 1.5s infinite', color:'var(--accent)' }}>Generating summary... 🧠</div>
                </div>
              ) : (
                <div>
                  <div style={{ background:'rgba(255,255,255,0.05)', padding:'15px', borderRadius:'12px', border:'1px solid rgba(255,255,255,0.1)', marginBottom:'12px' }}>
                    {summaryData?.text}
                  </div>
                  
                  {/* Action suggestions based on summary */}
                  <div style={{ background:'rgba(167,139,250,0.1)', padding:'12px', borderRadius:'8px', border:'1px solid rgba(167,139,250,0.3)' }}>
                    <div style={{ fontSize:'13px', fontWeight:'600', color:'var(--accent)', marginBottom:'8px' }}>
                      💡 Suggested Actions:
                    </div>
                    <div style={{ fontSize:'12px', color:'rgba(255,255,255,0.8)', lineHeight:'1.5' }}>
                      • Review your high-priority tasks from the dashboard
                      • Set up a focused work session for complex tasks
                      • Use voice input to capture spontaneous ideas
                      • Check your PINCH-categorized task lists
                    </div>
                  </div>
                  
                  {/* Quick stats */}
                  <div style={{ display:'flex', gap:'8px', marginTop:'12px' }}>
                    <div style={{ 
                      padding:'8px 12px', 
                      background:'rgba(255,255,255,0.05)', 
                      borderRadius:'6px', 
                      fontSize:'11px', 
                      color:'rgba(255,255,255,0.6)'
                    }}>
                      Next: Focus on Passion tasks
                    </div>
                    <div style={{ 
                      padding:'8px 12px', 
                      background:'rgba(255,255,255,0.05)', 
                      borderRadius:'6px', 
                      fontSize:'11px', 
                      color:'rgba(255,255,255,0.6)'
                    }}>
                      Energy: High
                    </div>
                    <div style={{ 
                      padding:'8px 12px', 
                      background:'rgba(255,255,255,0.05)', 
                      borderRadius:'6px', 
                      fontSize:'11px', 
                      color:'rgba(255,255,255,0.6)'
                    }}>
                      Priority: Balance
                    </div>
                  </div>
                </div>
              )}
           </div>
         </div>
       )}

      {/* ━━━━━━━━ AI SMART INPUT VIEW ━━━━━━━━ */}
      {view === 'aiSummary' && (
        <div className={`b-panel b-panel--tall b-panel--${panelAnim}`} style={{ flexDirection:'column', gap:12 }}>
          <button className="b-back" onClick={() => goTo('addMenu')}><BackIcon /></button>
          <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

          <div className="b-menu-title">AI Summary</div>
          <div className="b-menu-sub">Describe your task in plain words</div>

          <textarea
            className="b-textarea"
            placeholder="e.g. I need to finish the report by Friday, it's really important…"
            value={aiText}
            onChange={e => setAiText(e.target.value)}
            rows={4}
            autoFocus
          />
          <button className="b-submit-btn" onClick={() => submitTask('ai')} disabled={isLoading || !aiText}>
            {isLoading ? "Thinking..." : <><SparkleIcon /> Let AI Create Task</>}
          </button>
        </div>
      )}

      {/* ━━━━━━━━ MANUAL FORM ━━━━━━━━ */}
      {view === 'manual' && (
        <div className={`b-panel b-panel--form b-panel--${panelAnim}`}>
          <button className="b-back" onClick={() => goTo('addMenu')}><BackIcon /></button>
          <button className="b-close" onClick={() => goTo('icon')}><CloseIcon /></button>

          <div className="b-menu-title">New Task</div>

          <div className="b-form">
            {/* Title */}
            <div className="b-field">
              <label className="b-label">Task Title</label>
              <input className="b-input" placeholder="What needs to be done?"
                value={task.title}
                onChange={e => setTask(t => ({...t, title: e.target.value}))}
                autoFocus
              />
            </div>

            {/* Duration */}
            <div className="b-field">
              <label className="b-label">Duration</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input 
                  className="b-input" 
                  style={{ flex: 1 }}
                  placeholder="e.g. 45m, 1.5h, 30 minutes"
                  value={task.duration}
                  onChange={e => setTask(t => ({...t, duration: e.target.value}))}
                />
                <button
                  onClick={() => setTask(t => ({...t, duration: '30m'}))}
                  style={{ 
                    padding: '6px 12px', 
                    background: 'var(--accent)', 
                    color: 'white', 
                    border: 'none', 
                    borderRadius: '6px', 
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  30m
                </button>
                <button
                  onClick={() => setTask(t => ({...t, duration: '1h'}))}
                  style={{ 
                    padding: '6px 12px', 
                    background: 'var(--accent)', 
                    color: 'white', 
                    border: 'none', 
                    borderRadius: '6px', 
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  1h
                </button>
                <button
                  onClick={() => setTask(t => ({...t, duration: '2h'}))}
                  style={{ 
                    padding: '6px 12px', 
                    background: 'var(--accent)', 
                    color: 'white', 
                    border: 'none', 
                    borderRadius: '6px', 
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  2h
                </button>
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
                Try: 15m, 30m, 45m, 1h, 2h, half-day, full-day
              </div>
            </div>

            {/* Due date */}
            <div className="b-field">
              <label className="b-label">Due Date</label>
              <input className="b-input" type="date"
                value={task.due}
                min={new Date().toISOString().split('T')[0]}
                onChange={e => setTask(t => ({...t, due: e.target.value}))}
              />
            </div>

            {/* Priority - auto from due date */}
            {task.due && (
              <div className="b-priority-pill" style={{ borderColor: priorityMeta.color+'55', background: priorityMeta.color+'18' }}>
                <span className="b-priority-dot" style={{ background: priorityMeta.color }} />
                <span style={{ color: priorityMeta.color, fontWeight:700, fontSize:11 }}>
                  {priorityMeta.label}
                </span>
                <span className="b-priority-note">
                  {priority === 'overdue' ? 'Already overdue!' :
                   priority === 'urgent'  ? 'Due in less than a day' :
                   priority === 'high'    ? 'Due in 1-3 days' :
                   priority === 'medium'  ? 'Due in 3-7 days' :
                                           'Due in 7+ days'}
                </span>
              </div>
            )}

            {/* Notes */}
            <div className="b-field">
              <label className="b-label">Notes <span style={{color:'var(--text3)'}}>optional</span></label>
              <textarea className="b-input b-textarea-sm" placeholder="Any extra context…" rows={2}
                value={task.notes}
                onChange={e => setTask(t => ({...t, notes: e.target.value}))}
              />
            </div>

            <button className="b-submit-btn" onClick={() => submitTask('manual')}
              disabled={isLoading || !task.title}>
              {isLoading ? "Saving..." : <><PlusIcon /> Add Task</>}
            </button>
          </div>
        </div>
      )}

      {/* ━━━━━━━━ ORB ━━━━━━━━ */}
      <div
        id="bubble-icon"
        className={`b-orb${view !== 'icon' ? ' b-orb--open' : ''}`}
        onMouseDown={onOrbMouseDown}
      >
        <div className="b-ring" />
        <div className="b-ring" style={{ animationDelay: '.85s' }} />
        <BrainIcon />
      </div>

    </div>
  );
}
