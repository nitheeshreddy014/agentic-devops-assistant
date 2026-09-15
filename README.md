# Agentic DevOps Troubleshooting Assistant

An advanced, AI-powered incident investigation tool. Describe a DevOps problem and 8 specialist AI agents collaborate to triage, analyse, and guide you through resolution.

🌐 **Live Demo:** [https://agentic-devops-assistant-dzsrzybx6-nitheesh1.vercel.app/](https://agentic-devops-assistant-dzsrzybx6-nitheesh1.vercel.app/)

---

## What Was Improved (v2)

| # | Improvement | Why |
|---|-------------|-----|
| 1 | **Step pass/fail/can't-run toggles** | Tell the AI which steps failed or couldn't be run — no more dead-ends |
| 2 | **Escalation Panel** | After 2+ stuck iterations: download report, restart with context, try next root cause, copy Jira ticket |
| 3 | **Interactive Missing Info Panel** | Fill in missing answers inline — no need to restart the investigation |
| 4 | **Restart with context** | Pre-fills a new form with all previous findings carried over |
| 5 | **Session persistence** | Investigations survive page refresh via localStorage |
| 6 | **Investigation history drawer** | Last 10 sessions stored locally; click any to restore it |
| 7 | **Export / Download report** | Download full findings as a `.md` file or copy to clipboard |
| 8 | **Mark as Resolved** | Closes the loop; history entry marked green |
| 9 | **Error retry + smart messages** | Rate-limit, 401, 503 each show a specific fix; one-click Retry button |
| 10 | **Agent timeline — unique icons + duration** | Each agent has its own icon; click to expand full output |
| 11 | **Expandable agent messages** | Click any agent row to read its full reasoning |
| 12 | **Runbook citation inline viewer** | Click any citation badge to read the runbook snippet inline |
| 13 | **Root cause confirmation** | "This was it" button closes the loop per root cause |
| 14 | **Confidence filter** | Slider to hide low-confidence root causes |
| 15 | **Drag-and-drop file upload** | Drop log or config files directly onto the upload zone |
| 16 | **Example incidents quick-fill** | One click to pre-fill a realistic incident (CrashLoopBackOff, Terraform, GitHub Actions) |
| 17 | **Safe vs dangerous step separation** | Read-only steps shown first; approval-required steps in an orange section |
| 18 | **Pre-populated output textarea** | Textarea pre-filled with per-step comment headers |
| 19 | **Continue with no output** | Mark steps failed/blocked to continue even without command output |
| 20 | **GroqStatus setup modal** | Click the red badge for a 5-step setup guide |
| 21 | **Browser notifications** | Get notified when investigation completes, even if tab is in background |
| 22 | **Keyboard shortcuts** | `Cmd+Enter` submit · `Esc` dismiss · `Cmd+K` history |
| 23 | **ARIA labels & roles** | `role="alert"`, `role="region"`, `aria-live`, `aria-label` throughout |
| 24 | **Form draft auto-save** | Form data saved to localStorage as you type |
| 25 | **Char counter with warning** | Description counter turns orange at 80% of the 5000-char limit |
| 26 | **Copy Jira ticket text** | Pre-formatted incident summary ready to paste into any ticket system |

---

## Architecture

```
frontend/                    # Next.js 14 + TypeScript + Tailwind
├── app/
│   ├── page.tsx             # Main page — all features wired together
│   └── layout.tsx
├── components/
│   ├── InvestigationForm.tsx   # Form with examples, drag-drop, draft save
│   ├── DiagnosticPanel.tsx     # Steps with pass/fail/cant-run toggles
│   ├── MissingInfoPanel.tsx    # Inline answer inputs
│   ├── RootCausePanel.tsx      # Confidence filter, confirm button, citation viewer
│   ├── AgentTimeline.tsx       # Unique icons, duration, expandable rows
│   ├── FinalReport.tsx         # Export .md, copy, mark resolved
│   ├── EscalationPanel.tsx     # Dead-end recovery options
│   ├── HistoryDrawer.tsx       # Last 10 investigations sidebar
│   └── GroqStatus.tsx          # Setup modal
└── lib/
    ├── api.ts               # API client with health normalisation
    ├── types.ts             # Shared TypeScript types
    ├── storage.ts           # localStorage session + history helpers
    └── hooks/
        ├── useNotification.ts        # Browser Notification API
        └── useKeyboardShortcuts.ts   # Cmd+Enter, Esc, Cmd+K

api/                         # FastAPI + LangGraph backend
├── index.py                 # Routes, CORS, HMAC security, rate-limit retry
├── workflow/
│   ├── graph.py             # 8-agent LangGraph pipeline
│   └── state.py             # Shared investigation state
└── agents/                  # One file per specialist agent

tests/
├── conftest.py              # FakeLLM — never calls real API
└── backend/
    ├── test_agents.py       # 18 agent unit tests
    ├── test_endpoints.py    # 20 endpoint integration tests
    ├── test_rag.py          # 11 BM25 RAG tests
    ├── test_security.py     # 16 security tests
    └── test_tools.py        # 30 tool tests (95 total)

frontend/__tests__/
    ├── storage.test.ts           # localStorage helpers
    ├── MissingInfoPanel.test.tsx # Inline answer inputs
    ├── EscalationPanel.test.tsx  # Dead-end recovery
    ├── FinalReport.test.tsx      # Export, copy, mark-resolved
    └── AgentTimeline.test.tsx    # Icons, duration, expand/collapse
```

---

## Quick Start

### Backend
```bash
cd api
cp .env.example .env          # add GROQ_API_KEY=gsk_...
pip install -r requirements.txt
uvicorn index:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

### Tests
```bash
# Backend (95 tests)
cd tests && python -m pytest backend/ -v

# Frontend
cd frontend && npm test
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + Enter` | Submit investigation form |
| `Escape` | Dismiss error banner / close modal |
| `Cmd/Ctrl + K` | Open investigation history drawer |

---

## Example Incidents (Built-in Quick Fill)

Click **"Try an example"** on the form to instantly load:
- **Kubernetes CrashLoopBackOff** — payment-service pods restarting every 30s after deployment
- **Terraform AccessDenied** — S3 state bucket permission failure after credential rotation
- **GitHub Actions timeout** — Docker build timing out after adding ML model dependency

---

## Production Checklist

- [x] HMAC-signed investigation tokens (tamper-proof)
- [x] Secret redaction before LLM (API keys, passwords, private keys)
- [x] Dangerous command detection (rm -rf, curl | bash, terraform apply)
- [x] Human approval required for destructive steps
- [x] Rate-limit retry with exponential backoff (backend)
- [x] Input size limits (5 000 chars description, 50 000 chars logs)
- [x] ARIA labels and roles throughout
- [x] 95 automated backend tests
- [x] 5 frontend component test suites
- [ ] CORS: set `ALLOWED_ORIGINS` env var for production (currently `*`)
- [ ] Add session expiry to HMAC tokens for stricter security

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Get free key at console.groq.com/keys |
| `SECRET_KEY` | No | HMAC signing key (auto-generated if missing) |
| `GROQ_MODEL` | No | Model name (default: `llama-3.3-70b-versatile`) |
| `ALLOWED_ORIGINS` | No | CORS origins (default: `*`) |
