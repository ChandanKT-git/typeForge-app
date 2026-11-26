# TypeForge — Product Requirements Document

## Original Problem Statement
Build a premium AI-powered typing learning platform where users improve typing speed
while learning real concepts from selected domains such as Programming, DBMS, OS,
Networking, AI/ML and English. Unlike traditional typing tools that generate random
words, this platform must generate concept-based educational content dynamically using
AI, so users learn and type simultaneously. UI/UX must feel premium, distraction-free,
modern, and highly polished — comparable to Monkeytype, Notion, and Duolingo.

## User Choices (locked in v1)
- AI provider: **Groq** (user-supplied API key); default model `llama-3.3-70b-versatile`.
- Auth: **JWT email/password** with httpOnly cookies + Bearer fallback (cross-site safe).
- Domains: **Programming, DBMS, OS, Networking, AI/ML** (English deferred).
- Tracking: full history, charts, AI mistake analysis, personalised recommendations.
- Theme: **dark only**.

## Architecture
- **Backend**: FastAPI (`server.py`) — auth (`auth.py`), AI (`ai_service.py` via Groq SDK),
  sessions (`sessions_router.py`), topics catalog (`topics_router.py`). MongoDB via Motor.
- **Frontend**: React 19 + Tailwind + shadcn primitives. Path alias `@/`. Recharts for
  analytics, lucide-react for icons, sonner for toasts. Custom TypingArena with
  character-level feedback and a glowing caret.
- **Design**: "Terminal Luxury" — `#09090B` base, IBM Plex Mono for headings/typing,
  Inter for UI. Blue (#3B82F6) accent with glow, success green, rose error.

## What's been implemented (2026-04-28)
- Auth: register / login / me / logout / refresh with bcrypt + JWT (HS256).
- Admin seeding on startup; `/app/memory/test_credentials.md` written.
- Topics catalog: 5 domains × 12-15 topics × 3 difficulties.
- AI:
  - `POST /api/ai/generate` — concept-based passage + 3 notes (ASCII-sanitised).
  - `POST /api/ai/analyze` — weak keys, error patterns, recommendations, next topics.
  - `POST /api/ai/summary` — headline, bullets, memory hooks.
- Sessions: create / list / get-by-id / `stats/overview` (totals + last_30 + by_domain).
- Frontend pages: Landing, Login, Register, Dashboard, Practice, Results, History.
- Protected routes redirect to /login. Logout clears cookies + bearer token.
- 100% backend (22/22) + 100% frontend e2e tests passed (testing_agent_v3 iter 1).

## Iteration 2 — P1 features (2026-04-28)
- **AI difficulty auto-adaptation** — `/sessions/stats/overview` now returns
  `recommendation { difficulty, length, reason, based_on_sessions }` derived from the
  last 5 sessions. Dashboard shows an "auto-adapt" card with an apply button that
  updates difficulty + length pills.
- **Streak counter + daily goal** — same endpoint returns
  `streak { current, longest, today, goal, goal_met }`. Dashboard renders a Streak
  card (flame, longest), a Daily Goal card (progress bar, X-more nudge), and a
  goal-met badge when satisfied.
- **Per-keystroke timestamp logging** — `TypingArena` collects
  `[{t: ms, correct: bool}]` and forwards to `/api/sessions`. Backend persists.
  Results page builds a real rolling-window WPM curve from keystrokes (16 buckets,
  ~6s window). Backwards-compatible with old sessions.
- 32/32 backend pytest, 100% frontend e2e (testing_agent_v3 iter 2). One regression
  caught and fixed: list_sessions 500 due to keystrokes projection — kwargs now
  filter `None` so Pydantic default_factory applies.

## Backlog (P0 / P1 / P2)
- **P2**: leaderboard / shareable result card OG-image.
- **P2**: keyboard-layout heatmap built from accumulated weak_keys.
- **P2**: optional code-snippet specific scoring (penalise shift/symbol misses).
- **P2**: light theme toggle (currently dark-only per user choice).
- **P2**: timezone-aware streak (currently UTC day boundary).

## Test Credentials
See `/app/memory/test_credentials.md` or `.env.example` for instructions on setting up an admin user.
- Admin credentials should be passed via `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables in `.env`.
