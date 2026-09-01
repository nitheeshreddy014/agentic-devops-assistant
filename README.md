# Agentic DevOps Troubleshooting Assistant

A production-style portfolio project demonstrating **agentic AI** for DevOps incident investigation. This is **not** a chatbot or LLM wrapper — it uses LangGraph orchestration, CrewAI specialist agents, LangChain/Groq integration, BM25 RAG, and MCP-compatible stateless tools to conduct structured, evidence-based, iterative investigations with human-controlled remediation.

---

## Why Agentic — Not a Simple LLM Wrapper

| Capability | Simple Chatbot | This Project |
|---|---|---|
| Issue classification | ❌ | ✅ Triage Agent |
| Ordered investigation plan | ❌ | ✅ Planner Agent |
| Static log/config analysis | ❌ | ✅ MCP tools (no LLM needed) |
| Runbook RAG citations | ❌ | ✅ BM25 index, real filenames |
| Ranked root causes + evidence | ❌ | ✅ Root Cause Agent |
| Read-only diagnostic commands | ❌ | ✅ Troubleshooting Agent |
| Dangerous command detection | ❌ | ✅ Safety Reviewer Agent |
| Iterative investigation | ❌ | ✅ Stateless continuation |
| Human approval gating | ❌ | ✅ All infrastructure changes flagged |
| Final structured report | ❌ | ✅ Report Agent |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                            │
│  InvestigationForm → AgentTimeline → RootCausePanel → DiagPanel     │
│  FinalReport · GroqStatus · MissingInfoPanel                        │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ /api/*  (same-origin, Vercel routing)
┌─────────────────────────▼───────────────────────────────────────────┐
│                    FastAPI Backend (Vercel Python)                   │
│  POST /api/investigations        POST /api/investigations/continue   │
│  POST /api/rag/search            POST /api/analyze/{logs,config}     │
│  GET  /api/health                POST /api/upload                    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                   LangGraph Workflow (Orchestrator)                  │
│                                                                     │
│  triage → plan → analyze → rag_search → root_cause →               │
│  troubleshoot → safety_review → report                              │
│                                                                     │
│  Each node calls a CrewAI specialist agent via LangChain/ChatGroq   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities (CrewAI Specialist Roles)

| Agent | Role | Output |
|---|---|---|
| **Triage** | DevOps Triage Specialist | issue_category, severity, affected_services, error_codes, missing_info |
| **Planner** | Investigation Planning Specialist | ordered diagnostic_plan |
| **Log Analysis** | Log and Configuration Analysis Expert | log_findings, config_findings |
| **RAG Knowledge** | Knowledge Base Research Specialist | runbook_citations (real filenames) |
| **Root Cause** | Root Cause Analysis Expert | ranked probable_causes with evidence |
| **Troubleshooting** | DevOps Troubleshooting Specialist | diagnostic_steps, recommended_fixes |
| **Safety Reviewer** | Infrastructure Safety Reviewer | flagged_items, safety_approved |
| **Report** | Technical Report Writer | comprehensive final report |

---

## Framework Usage

| Framework | Role | Does NOT do |
|---|---|---|
| **LangGraph** | Main workflow orchestrator — state machine, node routing, iteration | No LLM calls |
| **CrewAI** | Specialist agent personas (role, goal, backstory) used in prompts | No orchestration |
| **LangChain** | ChatGroq integration, prompt templates, output parsing | No orchestration |

---

## LangGraph Workflow

```
START
  │
  ▼
triage ──► plan ──► analyze ──► rag_search ──► root_cause ──► troubleshoot ──► safety_review ──► report
                                                                                                      │
                                                                                                     END
Continuation (user provides diagnostic output):
  analyze ──► rag_search ──► root_cause ──► troubleshoot ──► safety_review ──► report ──► END
```

State is serialized as HMAC-SHA256-signed JSON and passed between frontend and backend — **no database or Redis required**.

---

## RAG Design

- **Retrieval**: BM25Okapi (`rank-bm25`) keyword search — **no embedding API, no paid vector database**
- **Knowledge base**: 16 bundled Markdown runbooks covering Terraform, Kubernetes, Docker, AWS, Azure, CI/CD, networking, database, SSL/TLS, Linux
- **Citations**: Real `filename§section` citations from the actual runbook files — never fabricated
- **Optional LLM re-ranking**: After BM25 retrieval, the RAG Knowledge Agent can use the LLM to select the most relevant results
- **Graceful degradation**: BM25 works without any LLM configured

---

## MCP-Compatible Tools (Stateless, Read-Only)

| Tool | Function |
|---|---|
| `log_parser.parse_logs()` | Pattern-match errors/warnings in log text |
| `terraform_analyzer.analyze_terraform()` | Detect Terraform errors, plan issues |
| `kubernetes_analyzer.analyze_kubernetes()` | Detect K8s YAML misconfigurations |
| `dockerfile_analyzer.analyze_dockerfile()` | Detect Dockerfile security/best-practice issues |
| `cicd_analyzer.analyze_cicd()` | Detect GitHub Actions / Jenkins / GitLab CI issues |
| `runbook_search.search_runbooks()` | BM25 runbook search |
| `checklist.get_checklist()` | Return diagnostic checklists per category |
| `command_safety.check_command_safety()` | Classify commands as safe/dangerous/approval-required |

All tools are stateless HTTP-compatible functions — no shell execution, no infrastructure modification.

---

## Security Controls

- **Secret redaction**: Passwords, tokens, API keys, private keys stripped from all user input before LLM calls
- **HMAC-signed state**: Investigation state is signed with SHA-256 — tampering is detected and rejected
- **Input size limits**: Logs ≤ 50 KB, configs ≤ 30 KB, descriptions ≤ 5 KB
- **File upload restrictions**: Only plain-text extensions allowed; binary/executable files rejected
- **No storage**: Uploaded files and logs are never persisted
- **Dangerous command detection**: All suggested commands classified by risk level
- **Human approval gating**: Every infrastructure-changing action marked `requires_approval: true`
- **API key never exposed**: Health endpoint reports `llm_configured: bool` — never the key value

---

## Local Development

### Prerequisites
- Python ≥ 3.11
- Node.js ≥ 18
- A free [Groq API key](https://console.groq.com) (optional — app starts without one)

### Backend

```bash
cd agentic-devops-assistant

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r api/requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=gsk_...

# Run FastAPI development server
uvicorn api.index:app --reload --port 8000
```

The API will be available at `http://localhost:8000/api/docs`.

### Frontend

```bash
cd agentic-devops-assistant/frontend

# Install dependencies
npm install

# Run Next.js development server
npm run dev
```

The app will be available at `http://localhost:3000`.  
In development, Next.js proxies `/api/*` → `http://localhost:8000/api/*` automatically.

---

## Testing

```bash
# Backend tests (never call Groq — FakeLLM only)
cd agentic-devops-assistant
pip install -r api/requirements.txt
pytest tests/ -v

# Frontend tests
cd frontend
npm install
npm test
```

Backend tests cover:
- Secret redaction and HMAC state signing/verification
- All 8 static analysis tools (no LLM)
- BM25 RAG retrieval and citation accuracy
- All 8 agents with FakeLLM (no quota)
- All FastAPI endpoints with TestClient

---

## Vercel Deployment

1. **Push** this repository to GitHub.
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import the GitHub repo.
3. Vercel auto-detects the `vercel.json` configuration.
4. In **Project Settings → Environment Variables** add:

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | `gsk_...` (your Groq key) |

5. Click **Deploy**.

That's it. No Docker, no Redis, no database, no separate backend URL.

---

## How to Obtain a Free Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in (no credit card required)
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key (starts with `gsk_`)

---

## Where to Add GROQ_API_KEY

| Environment | Location |
|---|---|
| Local development | `.env` file in `agentic-devops-assistant/` root |
| Vercel production | Project Settings → Environment Variables → `GROQ_API_KEY` |

**Never commit your API key.** The `.env` file is in `.gitignore`.

---

## How to Change the Groq Model

Edit `.env` (local) or Vercel Environment Variables:

```bash
LLM_MODEL=llama-3.1-8b-instant      # Faster, lower quality
LLM_MODEL=llama-3.3-70b-versatile   # Default — best quality (free tier)
LLM_MODEL=mixtral-8x7b-32768        # Good balance
LLM_MODEL=gemma2-9b-it              # Google Gemma via Groq
```

Current free-tier Groq models: [console.groq.com/docs/models](https://console.groq.com/docs/models)

---

## Free-Tier and Rate-Limit Notes

- Groq free tier: ~14,400 tokens/minute for most models
- The app handles HTTP 429 with exponential backoff (up to 3 retries)
- If rate-limited, the static analysis tools still work without LLM
- For heavy testing, use `llama-3.1-8b-instant` (higher rate limits)

---

## Sample Incidents

The system is designed to investigate these scenarios out-of-the-box:

| Incident | Technology | Key Runbooks |
|---|---|---|
| Terraform `AccessDenied` on `terraform apply` | Terraform + AWS | terraform-auth-errors, aws-iam-networking |
| Terraform state lock from crashed CI job | Terraform | terraform-state-locks |
| Kubernetes pod `CrashLoopBackOff` / `OOMKilled` | Kubernetes | kubernetes-crashloopbackoff |
| Docker container exits immediately (code 1) | Docker | docker-build-failures |
| Jenkins build failing out of disk space | Jenkins | jenkins-failures, linux-disk-memory-cpu |
| GitHub Actions secret not found | GitHub Actions | github-actions-failures |
| API returning HTTP 504 timeouts | API / networking | api-timeouts, dns-problems |
| DNS resolution failure inside Kubernetes | Kubernetes / DNS | dns-problems |
| PostgreSQL max_connections exceeded | Database | database-connectivity |
| Linux server disk 100% — writes failing | Linux | linux-disk-memory-cpu |
| SSL certificate expired — HTTPS failing | SSL/TLS | ssl-tls-problems |

---

## The Only Required Secret

```
GROQ_API_KEY=gsk_...
```

That is the only secret you need to provide. The app starts without it and shows  
**"LLM not configured"** instead of crashing. All static analysis tools work without any API key.
