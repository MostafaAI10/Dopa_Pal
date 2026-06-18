# Anchor — Full Product Vision & User Experience Documentation

*This document describes the complete, unconstrained version of the system — every feature from the original concept intact, with the corrected logic from the architectural review built in as a governing principle rather than a patch. It is meant to answer three questions for anyone reading it: what is this, how does it feel to use, and how does it work underneath.*

---

## 1. What Anchor Is

Anchor is an ambient cognitive secretary for people whose brains run on an interest-based nervous system rather than an importance-based one — most visibly people with ADHD, but the design holds for anyone who experiences time-blindness, task paralysis, or shame-driven avoidance around conventional to-do tools.

Conventional productivity software assumes the user has reliable working memory, stable executive function, and the ability to self-initiate around importance rather than interest. Calendars, Notion boards, and to-do apps all require the user to *maintain* the system — typing in tasks, estimating durations, remembering to check it, tolerating the guilt of a growing red overdue counter. For the population Anchor is built for, that maintenance burden is often the actual reason the tool gets abandoned, not laziness or lack of desire to be organized.

Anchor inverts the relationship. The system maintains itself. It pulls in obligations from the outside world, listens for tasks the user mentions in passing, watches how the user is doing each morning, and decides — quietly, in the background — what one thing to put in front of them right now. The user's only job is to look at one bubble and do one thing. Everything else is the system's responsibility.

---

## 2. Core Design Principles

Three corrections came out of reviewing the original flow against the neuropsychological constraints the system is meant to serve. They aren't edge-case fixes — they are the rules that every feature below has to obey.

**Energy scales depth, never density.** A high-energy morning should never mean a wall of tasks appears. It means the *one* thing in front of the user can be more demanding, or that a second optional "bonus" item is available if the user wants to chase it — but the visual experience of opening the bubble is identical on a good day and a bad day: one focused thing, never a list.

**The system never asks the user to fill in a blank.** When the task pool runs low, Anchor does not pop up an empty input box. An empty box is the exact blank-canvas paralysis the whole product exists to prevent. Instead, the system reaches into material it has already passively gathered — an unread syllabus update, a Slack message it noticed, a calendar event with no sub-tasks yet — and offers it as a single tappable suggestion. The user is never the one generating content from nothing; they're only ever confirming or declining something the system already drafted.

**Urgency is one input, not the ranking.** Sorting purely by deadline proximity trains the same anxiety-driven, last-minute-only engagement pattern Anchor is trying to replace. Every ranking decision blends deadline urgency with interest, novelty, and challenge level (PINCH), so the thing surfaced is the most *engageable* urgent thing, not just the most overdue one.

---

## 3. The Complete Feature Set

### 3.1 Zero-Friction Task Intake

Anchor never requires the user to open a blank list and type. Every path into the system is either passive or near-instant:

- **Full API synchronization** — live, two-way-aware connections to Google Calendar, Notion, Jira, and university/LMS portals (Canvas, Blackboard, Moodle), silently pulling deadlines, assignment updates, and ticket changes the moment they're posted upstream, with no manual import step ever required.
- **OS-level highlight-to-task** — the user highlights any text anywhere on their machine (an email, a PDF, a lecture slide, a Slack thread) and presses one global hotkey. The highlighted text is gone from the screen and back as a scheduled task within roughly a second.
- **Global speech-to-task** — a single hotkey, from anywhere, opens the mic. The user says whatever is in their head, however messy ("ugh I still need to email the professor about the thing, like by Thursday probably") and the system extracts the actual obligation from the rambling.
- **Ambient extraction from passive context** — for users who opt in, the system can also notice tasks implied in content it already has visibility into (an unread announcement, a Slack mention) and hold them as unverified candidates rather than tasks — never auto-committing something the user hasn't confirmed, but always having something ready to suggest the moment the queue runs low.

### 3.2 Smart Task Processing & Chunking

- **Algorithmic slicing** — any task estimated above a single working session is automatically broken into smaller sub-blocks sized to be completable in one sitting (default ~2 hours, user-adjustable).
- **Duration-deadline pacing** — sub-blocks are distributed across the full window before the deadline rather than clustered at the end, actively counteracting time-blindness by making distant deadlines feel present earlier.
- **Dynamic urgency + PINCH scoring** — every task carries a live urgency score (deadline proximity × remaining effort) blended with interest, novelty, challenge, and hurry signals, so what surfaces first is engaging *and* important, not just whichever clock is closest to zero.
- **Adaptive learning over time** — the longer the system runs, the more it learns the user's real patterns: which task types they consistently complete early versus avoid, how their stated effort estimates compare to actual time spent, and which interest tags reliably re-engage them. Pacing and ranking get progressively smarter as a result, rather than running on the same static formula forever.

### 3.3 State-Aware Initialization

This is the system's full "morning brain," matching the original metric set exactly:

- **Wake-up vs. startup delta** — the gap between when the user actually wakes and when they open the system, used as a signal for morning scrolling or avoidance.
- **Self-reported emotional state and energy** — a near-instant tap-based check, with an optional free-text or voice note for *why* the state is low today, which the system can use to soften its tone and choice of first task (a rough morning after a bad night's sleep gets a gentler first suggestion than a rough morning from boredom).
- **Work done before startup** — early, unprompted micro-actions logged before the formal session even begins, counted as a positive momentum signal.
- **User history** — rolling, longer-window pattern data (not just the last 48 hours) feeding into how aggressively the system paces the day.
- **The Dopamine Shield** — the full version: between detected wake time and the moment the user opens Anchor, the most distraction-heavy apps on the device (social media, short-form video) are genuinely locked at the OS level, not just nudged. The lock lifts the instant the user opens the floating bubble, so opening Anchor is never punished — it's the key that unlocks the rest of the phone or computer.

### 3.4 Dopamine-Aligned Reward Engine

- **Micro-customizations** — completing blocks unlocks visual changes to the bubble and dashboard itself: new accent colors, themes, animation styles — small, cosmetic, but genuinely novel each time, so the environment never goes stale.
- **Tactile feedback** — variable (not identical every time) audio cues and short animations on completion, tuned to feel satisfying rather than gimmicky.
- **Streaks without shame** — momentum is tracked and rewarded, but a broken streak is never displayed as a loss; it simply resets quietly with no "you broke your streak" messaging.
- **The Interest Vault** — completing a task periodically surfaces a short, high-quality fact or resource tied to whatever the user is currently into — a coding language they're learning, a topic they're hyper-fixated on this month — turning task completion into something that occasionally also feeds the thing they actually want to think about.

---

## 4. The End-to-End System Flow

This section walks the flowchart you provided node by node, with the corrected logic written directly into each step rather than left as a separate caveat.

**Ring Phone / Notification, between wake-up and startup, with optional phone lock.** The moment the system detects the user is awake (via a wearable signal, phone unlock pattern, or a simple first-unlock timestamp), the Dopamine Shield optionally engages. This is the only point in the entire system that resembles a traditional notification, and even this is a single, calm prompt rather than a flashing alert.

**Software System (Floating Bubble) opens at wakeup / after startup.** The bubble is the first and only thing the user is asked to look at. Opening it is what lifts the Dopamine Shield, making engagement with Anchor the path of least resistance compared to anything else on the device.

**User State Evaluation.** All seven signals from §3.3 (wake/startup delta, app startup time, emotional state, energy, pre-startup work, optional reason for low state, user history) feed into a single state score.

**High Score branch.** In the original flow this led to "give many tasks." In the corrected system, a high score never increases how many things are *visible* — it increases how demanding the single primary task is allowed to be, and unlocks up to two optional bonus items the user can choose to chase if they want to ride the momentum. The bubble still shows one thing first.

**Low Score branch → "Less Tasks."** This stays intact: a low score genuinely restricts the system to the smallest, lowest-friction version of the next step — sometimes as small as "open the document" with no actual content work attached yet.

**Check Database for tasks → amount of given tasks.** Whichever branch the user came from, the system checks whether it actually has enough material queued to support that level of engagement today.

**Enough Tasks? — Yes.** The system gives tasks sorted not by raw urgency but by the blended urgency-plus-PINCH score described in §2, and renders them as a single highlighted task at a time, never a list, regardless of how many are technically queued behind it.

**Enough Tasks? — No.** This is the node that most needed correcting. The original flow asked the user to manually add tasks here — exactly the blank-canvas moment Anchor is designed to avoid. In the corrected flow, the system instead surfaces one ambient suggestion drawn from material it already has (an unread calendar event, a passively noticed Slack mention, a syllabus update) as a single tappable card: confirm, edit in one tap, or dismiss. Manual speech and highlight intake (bottom-left sticky note) remain available at all times as user-initiated paths, but the system never forces the user into that mode — it only offers it as one of several doors.

**User Finished Tasks → Reward User → loop continues.** Completion triggers the reward engine (§3.4), and the loop feeds back into the task-supply check rather than ending — Anchor is not a once-a-day check-in, it's a continuous ambient loop that keeps re-evaluating supply and state throughout the day every time something gets completed, not just once at boot.

---

## 5. How It Works Internally

Underneath the bubble, six cooperating engines do the actual work. None of them are visible to the user; together they're what makes the single-focus experience above possible.

**The Ingestion & Translation Engine** is the front door for every intake path — API sync, highlight capture, voice transcript, or ambient passive extraction. Regardless of source, everything funnels through the same NLP layer, which strips noise (signatures, boilerplate, corporate filler) and isolates the actual action item, a deadline if one exists, and a rough effort estimate. Output is always the same shape: a clean task draft, never raw text, by the time anything reaches storage.

**The State Evaluation Engine** runs at boot and periodically through the day, combining the seven signals from §3.3 into the live state score. This score isn't binary high/low in practice — it's a continuous value, and the Density Governor downstream treats it as a dial rather than a switch, so the difference between a 40 and a 60 produces a noticeably different but never jarring experience.

**The Contextual Recommendation Engine** owns the ranking logic — blending urgency, PINCH signals, and (over time) the adaptive learning layer that's noticed which task types this specific user actually follows through on. This is also the engine responsible for the chunking/pacing math: taking a parent task's estimated effort and deadline and producing the actual sequence of sub-blocks, then re-flowing that sequence whenever the user adjusts pacing from the dashboard or whenever a block gets skipped.

**The Ambient Ingestion Layer** sits behind the "Enough Tasks?" decision specifically — it's a standing pool of unverified candidates (synced calendar items not yet broken into sub-tasks, passively noticed mentions) that the system draws from instead of ever prompting a blank input.

**The Reward Engine** listens for completion events and decides, based on streak state and unlock history, whether this completion triggers a cosmetic unlock, an Interest Vault drop, both, or just the baseline tactile feedback — keeping rewards variable rather than mechanically identical every time.

**The Ambient UX Layer** is the thin presentation layer translating all of the above into the bubble and dashboard. It is intentionally the "dumbest" layer in the system: it never makes a ranking or scoring decision itself, it only ever renders whatever the engines below it have already decided is the single right thing to show.

---

## 6. Who It's For

**Mariam**, a university student, has a mind that runs on hyperfocus and crash cycles. She can disappear into a project for six hours straight or be completely unable to start one for three days, with no in-between. Conventional planners assume steady daily effort; Anchor's pacing engine instead treats her output as naturally uneven and just makes sure the *sum* of sub-blocks lands before the deadline, regardless of which days she actually does the work.

**Youssef**, an early-career backend developer, doesn't struggle with starting work — he struggles with remembering that work exists at all once it's out of sight. His failure mode isn't avoidance, it's object permanence: a ticket assigned in a stand-up is functionally gone the moment the meeting ends unless something re-surfaces it. For him, the value of Anchor is almost entirely in the passive intake layer — the system remembering on his behalf.

---

## 7. A Day in the Life

**A good morning.** Mariam wakes up, unlocks her phone forty seconds later, opens Anchor almost immediately after. The Dopamine Shield never even had a chance to engage — the gap was too small to register as avoidance. The one-tap mood check comes back high. The bubble doesn't throw a list at her; it shows one task — "Draft the literature review intro, 45 minutes" — with a second, optional bonus item faintly visible underneath in case she wants to chain into it. She does. Forty minutes later she taps complete on the first, and a new accent color unlocks across the whole interface. She keeps going into the bonus item without ever having to consciously decide to "do more work" — the system just made staying easier than stopping.

**A rough morning.** Youssef wakes up anxious about a deadline he's been avoiding thinking about. He doesn't open Anchor for forty minutes — he's scrolling. When he finally opens it, the Dopamine Shield had already quietly locked his social apps the moment his sleep tracker registered him as awake, so opening Anchor is what gets him his phone back in any useful form. The state score comes back low. There's no scolding, no streak warning. The bubble shows exactly one thing: "Open the proposal doc and write one sentence." That's the entire ask. He does it in ninety seconds. The system doesn't escalate to a second task — it lets the win stand alone.

**The empty queue moment.** Mid-afternoon, Mariam finishes everything that was queued. In the old design this is where she'd be handed a blank box and asked to type something — exactly the moment she's most likely to just close the app instead. In the corrected flow, the bubble instead shows a single soft card: "Your Database Systems course posted a new assignment yesterday — want me to turn it into a plan?" One tap and it's chunked and paced before she's even fully read the deadline.

**A missed day.** Youssef doesn't open the app at all on Thursday. There is no red badge waiting for him Friday, no "you have 3 overdue tasks" banner. The pacing engine quietly absorbed Thursday's planned block, redistributed it across the remaining days before the deadline, and Friday's bubble shows exactly one task like always — slightly larger in scope to account for the lost day, but still just one thing.

**Evening dashboard check-in.** Mariam opens the Command Dashboard, the only time all day she sees the full picture rather than a single task. She drags the pacing slider on her thesis proposal from "due in three weeks" to "finish by next Friday" because she suddenly has a clear week ahead. The moment she releases the slider, every remaining sub-block reflows, and the next morning's bubble is already showing the new, tighter first step.

---

## 8. Interface Walkthrough

**The Ambient Bubble**, the user's daily-driver surface, lives permanently at the edge of the screen and never resizes itself unprompted, never flashes, never carries a badge count. Clicking it expands a single focused card: the current task, its sub-block detail, a complete button, and the same voice/highlight intake controls available globally via hotkey. Completing the visible task triggers the reward animation in place, then the bubble either loads the next item (if a bonus task was available) or collapses back to its resting state.

**The Command Dashboard** is the macro-view, opened deliberately rather than encountered passively. It shows the full task map — parent goals alongside their generated sub-blocks — with drag-and-drop reordering, a per-task pacing slider, an integrations panel for connecting Calendar/Notion/Jira/LMS accounts, and a rewards shelf showing unlocked themes, current streak state (always framed positively, never as a countdown to failure), and the Interest Vault history.

---

## 9. Flowchart-to-System Mapping

| Original Flowchart Node | What It Becomes in the Full System | Why |
|---|---|---|
| Ring Phone / Notification + optional phone lock | Full Dopamine Shield, OS-level app lock between wake and startup, lifted on bubble open | Removes early-morning attention fracturing without punishing the user for delay |
| Software System (Floating Bubble) | Persistent ambient overlay, never resized or flagged | Keeps the system invisible until needed |
| User State Evaluation (sticky-note metrics) | State Evaluation Engine, all seven signals retained including optional "reason for low state" and full user history | Full signal set preserved exactly as specified |
| High Score → Give many tasks | High score scales task *depth/complexity* and unlocks up to two optional bonus items; visible density stays at one | Prevents cognitive dread even on good days |
| Low Score → Less Tasks | Unchanged — restricts to the smallest possible next step | Already correctly designed in the original flow |
| Check Database for tasks / Enough Tasks? | Ambient Ingestion Layer check, feeding the Contextual Recommendation Engine | Same decision point, smarter material behind it |
| Give tasks sorted by urgency, highlight single tasks | Urgency + PINCH blended ranking, still rendered as one highlighted task | Avoids pure-urgency anxiety sorting while keeping single-focus rendering |
| Ask the user to add tasks | Ambient extraction chip surfacing a pre-parsed candidate for one-tap confirmation | Eliminates blank-canvas paralysis |
| Reward User / User Finished Tasks loop | Reward Engine fires, loop feeds back into the supply check continuously through the day | Matches the original's intent of a recurring cycle, not a one-time morning flow |

---

## 10. The Design Promise

Every feature above exists in service of one rule: Anchor is allowed to ask the user to do exactly one thing at a time, and nothing else. It is allowed to be wrong about pacing, wrong about mood, even wrong about what's interesting this week — what it is never allowed to do is make the user feel behind.
