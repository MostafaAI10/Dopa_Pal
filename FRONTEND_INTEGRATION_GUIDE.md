# DopaPal Frontend Integration Guide 🚀
**Status: FINAL HACKATHON VERSION - ALL BACKEND/AI SYSTEMS GREEN 🟢**

This guide contains everything you need to connect the frontend to the AI-powered backend. The backend is running perfectly on `http://localhost:8000/api/v1`. All endpoints are fully tested and bug-free.

---

## 🛠️ Global Configuration
For all HTTP requests, use these settings:
- **Base URL:** `http://localhost:8000/api/v1`
- **Headers:** `Content-Type: application/json`

*(Note: During local dev/hackathon, CORS is fully open `*`, so you will not face CORS errors).*

---

## 1. Smart Task Ingestion (AI-Powered) 🤖
When the user speaks to the app, highlights text, or types a random sentence, send it here. The AI will extract dates, estimate hours, categorize the task, and chunk it intelligently.

**Endpoint:** `POST /tasks/ingest`

### Request Data (JSON)
```typescript
interface IngestRequest {
  source_text: string; // The raw sentence, e.g., "Finish the chemistry paper by Monday, around 5 hours"
  source_type: string; // "highlight", "voice", "manual", or "calendar"
}
```

### TypeScript / Fetch Example
```javascript
async function ingestTask(text, type) {
  const response = await fetch("http://localhost:8000/api/v1/tasks/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_text: text,
      source_type: type
    })
  });
  
  if (!response.ok) throw new Error("Ingestion failed");
  return await response.json(); // Returns Task Object
}
```

---

## 2. Manual Task Creation 📝
If the user uses the structured form UI (Title, DatePicker, Hours Input). It skips text parsing but **still runs the AI chunking and scoring engine**.

**Endpoint:** `POST /tasks/create`

### Request Data (JSON)
```typescript
interface CreateRequest {
  title: string;
  deadline: string; // ISO String, e.g., "2026-06-25T18:00:00"
  estimated_hours: number; // e.g., 2.5
  interest_tag?: string; // Optional, e.g., "chores" or "programming"
  source_type: string; // Usually "manual" here
}
```

### 💡 Backend Response (Shared for both Ingest & Create):
You will receive this object. **You do not need to display all of it**, but save it to state.
```json
{
  "id": 1,
  "title": "Finish the chemistry paper",
  "deadline": "2026-06-22T23:59:59",
  "estimated_hours": 5.0,
  "interest_tag": "science",
  "status": "pending",
  "pinch_score": 72.5,
  "sub_blocks": [
    {
      "id": 10,
      "sequence": 1,
      "duration_minutes": 120,
      "scheduled_date": "2026-06-20",
      "status": "pending"
    },
    // ... more chunks
  ]
}
```

---

## 3. The "Focus Bubble" (The Main Dashboard) 🎯
**This is the most important screen in the app.** It tells the ADHD user exactly what to do *right now*, without overwhelming them. It dynamically adapts based on their current cognitive state.

**Endpoint:** `GET /bubble/next`

### TypeScript / Fetch Example
```javascript
async function getNextFocusBubble() {
  const response = await fetch("http://localhost:8000/api/v1/bubble/next");
  const data = await response.json();
  
  // Frontend UI Logic:
  if (data.mode === "chill") {
      // User is low energy (< 50). Hide bonus blocks! Only show primary block.
      renderPrimaryBlock(data.primary_block);
  } else {
      // User is high energy (>= 50). Show primary block AND bonus blocks as options.
      renderPrimaryBlock(data.primary_block);
      renderBonusBlocks(data.bonus_blocks);
  }
}
```

### Response Example:
```json
{
  "state_score": 75.0,
  "mode": "focused", // "focused" or "chill"
  "primary_block": {
    "sub_block_id": 10,
    "task_title": "Finish the chemistry paper",
    "duration_minutes": 120,
    "pinch_score": 72.5,
    "interest_tag": "science"
  },
  "bonus_blocks": [ // ONLY display these if mode === "focused"
    {
      "sub_block_id": 11,
      "task_title": "Clean the garage",
      "duration_minutes": 60,
      "pinch_score": 68.2
    }
  ]
}
```

---

## 4. Completing a Task Block & Getting Rewards 🏆
When the Pomodoro timer ends or the user clicks "Done" on a block.

**Endpoint:** `POST /tasks/{sub_block_id}/complete`

### TypeScript / Fetch Example
```javascript
async function completeBlock(blockId) {
  const response = await fetch(`http://localhost:8000/api/v1/tasks/${blockId}/complete`, {
    method: "POST"
  });
  const data = await response.json();
  
  // Trigger animations if rewards are unlocked!
  if (data.unlocked_theme) {
    triggerThemeUnlockAnimation(data.unlocked_theme);
  }
  if (data.interest_vault_fact) {
    showFunFactModal(data.interest_vault_fact);
  }
  
  // Refresh the Focus Bubble after completion
  getNextFocusBubble();
}
```

---

## 5. Live WebSocket Updates ⚡ (Optional but Impressive)
To make the app feel magical, connect to the WebSocket when the app loads. You don't need to poll the API; the server will tell you when tasks are parsed.

**Endpoint:** `ws://localhost:8000/api/v1/ws/1` *(Using user ID 1 for the hackathon)*

### Implementation Example:
```javascript
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/1");

ws.onopen = () => console.log("Connected to DopaPal AI 🧠");

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.event === "task_ingested") {
    // Show a toast: "AI successfully organized: [Task Title]"
    showToast(`AI added: ${message.data.title}`);
    
    // Refresh the bubble in case this new task is higher priority
    getNextFocusBubble();
  }
  
  if (message.event === "block_completed") {
    // Trigger confettii
    fireConfetti();
  }
};
```

### 💡 Quick Checklist for the Frontend Dev:
- [ ] Connect the AI Input Box to `POST /tasks/ingest`
- [ ] Render the Main Dashboard using `GET /bubble/next` (Make sure to hide `bonus_blocks` if `mode === "chill"`)
- [ ] Connect the "Done" button to `POST /tasks/{id}/complete`
- [ ] (Bonus) Hook up the WebSocket for live toast notifications.

**You're all set. The backend is bulletproof. Go crush the hackathon! 🔥**
