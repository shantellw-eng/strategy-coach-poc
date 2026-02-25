# Marvin Strategy Coach — Project Context
> Paste this at the start of any new Claude conversation to restore context.
> Last updated: February 2026

---

## What Is This?
Marvin is an AI strategy coaching agent built for the **Australian Centre for Business Growth (Adelaide University)**. It guides SME leaders through a structured 5-step strategy development process, producing a clear Strategy Statement they can actually use.

It is being built by Shantell as both:
- A POC for the Centre
- A personal learning project for working with Anthropic/Claude

---

## Current Status
- ✅ POC built in **Streamlit + Python + Anthropic API**
- ✅ 5-step flow working: Objective → Scope → Advantage → Draft → Refine
- ✅ Live sidebar showing "Working Strategy" as session progresses
- ✅ Workshop / Board modes
- ✅ Quick action buttons (Revise objective, Revise scope, etc.)
- ✅ Claude Code installed on Windows (PowerShell)
- 🔄 Next focus: Enrich system prompt with Centre's frameworks
- 🔄 Visual aids panel (right-hand panel, front-end toggle)

---

## Key Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| Stack | Stay with Streamlit (for now) | Prove coaching quality first; migrate to Next.js when real auth/logging needed |
| Architecture | Hub and spoke (multi-coach) | Delegation, org design coaches to follow; strategy is coach #1 |
| Visual aids | Right-hand panel with toggle | Non-intrusive; keeps conversation primary; toggle is front-end not agent |
| Framework approach | Full Porter/Bain/BSC depth, Centre's voice | Agent applies full frameworks but through the Centre's lens, not generic MBA |
| System prompt structure | Modular | Easy to add new materials as Centre drip-feeds content |
| Claude.ai vs Claude Code | Both | Claude.ai for thinking/prompts/architecture; Claude Code for writing code |

---

## The Centre's Methodology (from GS7 Strategy deck)

### Core Definition
> "Strategy is identifying what is distinctive about your business, then using, preserving and extending that difference through decisions and actions that enable your company to achieve sustainable, competitive advantage."

### The Strategy Statement Structure
Three components (the Edwards Jones model):
- **Objective** = Ends (specific, measurable, time-bound, growth-focused)
- **Scope** = Domain (who you serve, psychographic not just demographic)
- **Advantage** = Means (your competitive advantage — what competitors can't easily copy)

Example:
> *"To grow to 17,000 financial advisers by 2012 by offering trusted and convenient face-to-face financial advice to conservative individual investors who delegate their financial decisions, through a national network of one-financial-adviser offices."*

### Key Frameworks Referenced
- **Porter**: Generic strategies (cost leadership, differentiation, focus); difference ≠ efficiency
- **Bain**: B2B and B2C Elements of Value pyramids (functional → emotional → life-changing → social)
- **Drucker**: Five Questions (Who are you? Who are your customers? What do they value? How are you measuring? What's the plan?)
- **Balanced Scorecard** (Kaplan & Norton): Financial, Customer, Processes, Learning & Growth
- **Strategic Sweet Spot**: Venn of your competitive advantage / unmet customer needs / competitor weaknesses

### Critical Distinction Marvin Must Enforce
Operational improvement ≠ strategy. If a user says "we provide better service" or "we're faster" — Marvin should challenge this as efficiency, not advantage.

---

## What's Wrong With the Current POC
- Too generic — coaching around the frameworks rather than through them
- Doesn't use the Centre's specific language and IP
- Doesn't do the Strategic Sweet Spot diagnostic before drafting
- Doesn't challenge "efficiency answers" with Porter's distinction
- Doesn't probe customer value with Bain's pyramid
- No visual aids at key transition points

---

## Planned Visual Aids (POC scope)
| Moment | Visual |
|---|---|
| Before Scope step | Bain value pyramid (B2B or B2C depending on business) |
| Before Advantage step | Strategic Sweet Spot diagram |
| At Draft step | Edwards Jones annotated example |
| At end | Clean strategy statement "card" (exportable) |

---

## Architecture Notes

### Current (Streamlit POC)
- Python + Streamlit
- Anthropic API (Claude)
- Single coach (Strategy)

### Future (Next.js)
Trigger for migration: when Centre wants real users, auth, and usage logging.
- Next.js frontend
- NextAuth / Clerk for authentication
- API routes (keep Anthropic key server-side)
- Usage logging dashboard for Centre
- Hub and spoke: Strategy → Delegation → Org Design coaches

### Prompt Structure (modular)
1. Core coaching behaviour and tone
2. Centre's strategy definition and principles
3. Framework depth (Porter, Bain, BSC) — grows as materials arrive
4. Industry/context specific knowledge (future)

---

## Materials Received
- [x] GS7 - Strategy.pptx (Growth Stopper #7)
- [ ] More decks to come as Centre gains confidence in the project

---

## Open Questions / To Do

### Coaching Quality
- [ ] Draft enriched system prompt embedding Centre's frameworks
- [ ] Define graceful "depth ceiling" behaviour (when Marvin reaches edge of its knowledge)
- [ ] Version control system prompts from day one

### UX / Front-end (Ryan's feedback)
- [x] Fix progress indicator — draft/refine logic corrected via is_locked
- [ ] Move Reset button from left panel to main panel (left panel too "techy")
- [ ] Left panel: hidden by default, shown on demand (simple toggle button on main panel)
- [ ] Fix Reset behaviour — clears chat and restarts from Step 1, does NOT go to login screen
- [ ] Build right-panel visual aids with front-end toggle
- [ ] Advantage not populating in sidebar panel (low priority — panel is test-only for now)
- [ ] Add Orientation data to left panel (B2B/B2C, industry, team size) — do after V11 system prompt
- [ ] Phase not advancing to "draft" when Marvin generates draft statement (STATE_JSON bug)

### Phase Structure Redesign
Revised 6-phase structure (from 5):

```
0. Orientation       <- new: B2B/B2C, industry, team size (2-3 questions, silent context)
1. Objective
2. Scope
3. Advantage
4. Strategy Statement  <- draft + refined combined into one step
5. Commit              <- commitment question gets its own dedicated step
```

This requires:
- System prompt V11 updated to reflect new phase names, Orientation phase, and Bain framework
- PHASES list in coach_bot_ui.py updated
- Orientation data (B2B/B2C, industry, team size) added to left panel display
- Commit step rendered as a distinct visual moment (card/highlighted block), not just another chat message
- Commit step becomes its own trackable data point for the Centre reporting

### System Prompt V11 — Key Changes from V10
- Add Orientation phase (B2B/B2C, industry, team size)
- Apply Bain B2B or B2C value pyramid in Scope phase based on Orientation context
- Embed Porter difference-vs-efficiency test in Advantage phase
- Add Strategic Sweet Spot check before drafting
- Update current_phase values: orientation | objective | scope | advantage | strategy_statement | commit
- Commit becomes explicit phase, not just a closing question

### Architecture
- [ ] Git init and baseline commit before any restructuring
- [ ] Restructure codebase for hub-and-spoke scalability (see proposed structure below)
- [ ] Decide on session persistence approach in Streamlit

## Proposed Folder Structure
```
gs1-bot/
├── coaches/
│   ├── strategy/        ← active
│   └── delegation/      ← parked, ready when needed
├── core/                ← shared engine, retrieval, KB pipeline
├── ui/                  ← Streamlit app
├── data/                ← vectors, models
└── assets/              ← images, visuals for the UI panel
```

---

## How We Work
- **Claude.ai**: Strategic thinking, architecture, drafting/reviewing prompts
- **Claude Code**: Writing and editing actual code in the project
- **This file**: Paste at start of new Claude.ai conversation to restore context
- **Prompt changes**: Treat like code — version control, note what changed and why
