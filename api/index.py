"""
FastAPI application – all API endpoints for the Agentic DevOps Troubleshooting Assistant.
Vercel exposes this file as the Python serverless function at /api/*.
"""
from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.core.config import get_settings
from api.core.logging_config import configure_logging, get_logger
from api.core.security import (
    generate_request_id,
    redact_secrets,
    sign_state,
    validate_filename,
    validate_text_input,
    verify_and_load_state,
)
from api.models.schemas import HealthResponse, RAGSearchRequest
from api.providers.llm_provider import get_llm
from api.rag.retriever import get_retriever
from api.tools.cicd_analyzer import analyze_cicd
from api.tools.dockerfile_analyzer import analyze_dockerfile
from api.tools.kubernetes_analyzer import analyze_kubernetes
from api.tools.log_parser import parse_logs
from api.tools.terraform_analyzer import analyze_terraform
from api.workflow.graph import build_continuation_graph, build_initial_graph
from api.workflow.state import make_initial_state

settings = get_settings()
logger = get_logger(__name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=3)


# ── Lazy graph singleton (Vercel serverless-compatible) ──────────────────────
# Vercel does NOT call FastAPI lifespan events — graphs must be built lazily.

_initial_graph      = None
_continuation_graph = None
_graph_lock         = asyncio.Lock()

configure_logging(settings.log_level)


async def _ensure_graphs():
    """Build LangGraph workflows once and cache at module level."""
    global _initial_graph, _continuation_graph
    if _initial_graph is not None:
        return
    async with _graph_lock:
        if _initial_graph is not None:
            return
        llm = get_llm()
        if llm is None:
            logger.warning("GROQ_API_KEY not set — AI agents disabled.")
        try:
            _initial_graph      = build_initial_graph(llm)
            _continuation_graph = build_continuation_graph(llm)
            logger.info("LangGraph workflows compiled OK")
        except Exception as exc:
            logger.error(f"LangGraph compilation failed: {exc}", exc_info=True)
            _initial_graph      = None
            _continuation_graph = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    await _ensure_graphs()
    yield
    _EXECUTOR.shutdown(wait=False)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agentic DevOps Troubleshooting Assistant",
    description=(
        "Multi-agent DevOps troubleshooting powered by LangGraph orchestration, "
        "CrewAI specialist agents, LangChain+Groq LLM integration, and BM25 RAG."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS: same-origin in Vercel production; permissive for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _request_id_middleware(request: Request, call_next):
    request.state.request_id = generate_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _run_graph(graph: Any, state: dict) -> dict:
    """Run synchronous LangGraph in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_EXECUTOR, graph.invoke, state)


def _slim_state(state: dict) -> dict:
    """Truncate large lists before HMAC-signing the state token."""
    t = dict(state)
    caps = {
        "log_findings": 12, "config_findings": 8, "runbook_citations": 5,
        "agent_messages": 20, "diagnostic_steps": 15, "recommended_fixes": 8,
        "probable_causes": 5, "diagnostic_plan": 12,
    }
    for k, cap in caps.items():
        if k in t and isinstance(t[k], list):
            t[k] = t[k][:cap]
    text_caps = {
        "logs_redacted": 600, "config_redacted": 500, "problem_description": 800,
    }
    for k, cap in text_caps.items():
        if k in t and isinstance(t[k], str):
            t[k] = t[k][:cap]
    return t


def _state_to_dict(state: dict, req_id: str, token: str) -> Dict[str, Any]:
    return {
        "session_id":          state.get("session_id", ""),
        "request_id":          req_id,
        "phase":               state.get("current_phase", "complete"),
        "issue_category":      state.get("issue_category", "unknown"),
        "severity":            state.get("severity", "unknown"),
        "missing_info":        state.get("missing_info", []),
        "affected_services":   state.get("affected_services", []),
        "error_codes":         state.get("error_codes", []),
        "agent_messages":      state.get("agent_messages", []),
        "diagnostic_plan":     state.get("diagnostic_plan", []),
        "log_findings":        state.get("log_findings", []),
        "config_findings":     state.get("config_findings", []),
        "runbook_citations":   state.get("runbook_citations", []),
        "probable_causes":     state.get("probable_causes", []),
        "diagnostic_steps":    state.get("diagnostic_steps", []),
        "recommended_fixes":   state.get("recommended_fixes", []),
        "flagged_items":       state.get("flagged_items", []),
        "report":              state.get("report") or {},
        "investigation_token": token,
        "llm_configured":      settings.llm_configured,
        "iteration":           int(state.get("iteration", 1)),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check — reports LLM status; NEVER exposes the API key."""
    return {
        "status":        "ok",
        "version":       settings.app_version,
        "llm_configured": settings.llm_configured,
        "llm_provider":  settings.llm_provider,
        "llm_model":     settings.llm_model,
        "request_id":    request.state.request_id,
    }


@app.post("/api/investigations")
async def start_investigation(request: Request):
    """
    Start a new agentic DevOps investigation.
    Runs: triage → plan → analyze → rag_search → root_cause → troubleshoot → safety_review → report
    Returns a stateless HMAC-signed investigation_token for continuation.
    """
    req_id = request.state.request_id
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body.")

    problem_title       = str(body.get("problem_title", ""))[:200]
    problem_description = str(body.get("problem_description", ""))
    technology          = str(body.get("technology", "unknown"))
    environment         = str(body.get("environment", "unknown"))
    recent_changes      = str(body.get("recent_changes", "") or "")
    raw_logs            = str(body.get("logs", "") or "")
    raw_config          = str(body.get("configuration", "") or "")

    # Input validation
    try:
        validate_text_input(raw_logs,   settings.max_log_size,         "logs")
        validate_text_input(raw_config, settings.max_config_size,      "configuration")
        validate_text_input(problem_description, settings.max_description_size, "problem_description")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    logs_redacted   = redact_secrets(raw_logs)
    config_redacted = redact_secrets(raw_config)

    await _ensure_graphs()
    graph = _initial_graph
    if graph is None:
        raise HTTPException(status_code=503, detail="Investigation graph not ready. Retry in a moment.")

    initial = make_initial_state(
        session_id          = str(uuid.uuid4()),
        request_id          = req_id,
        problem_title       = problem_title,
        problem_description = problem_description,
        technology          = technology,
        environment         = environment,
        recent_changes      = recent_changes,
        logs_redacted       = logs_redacted,
        config_redacted     = config_redacted,
    )

    try:
        result = await _run_graph(graph, initial)
    except Exception as exc:
        logger.error(f"Investigation graph failed [{req_id}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Investigation failed — check server logs.")

    token = sign_state(_slim_state(result))
    return JSONResponse(content=_state_to_dict(result, req_id, token))


@app.post("/api/investigations/continue")
async def continue_investigation(request: Request):
    """
    Continue an investigation with new diagnostic command output.
    Verifies the HMAC-signed state token, re-runs analysis agents,
    updates root causes and recommendations.
    """
    req_id = request.state.request_id
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body.")

    token           = str(body.get("investigation_token", ""))
    diagnostic_out  = str(body.get("diagnostic_output", ""))[:5000]

    try:
        state = verify_and_load_state(token)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    state["user_diagnostic_output"] = diagnostic_out
    state["iteration"]               = int(state.get("iteration", 1)) + 1
    state["request_id"]              = req_id

    await _ensure_graphs()
    graph = _continuation_graph
    if graph is None:
        raise HTTPException(status_code=503, detail="Continuation graph not ready.")

    try:
        result = await _run_graph(graph, state)
    except Exception as exc:
        logger.error(f"Continuation graph failed [{req_id}]: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Continuation failed — check server logs.")

    new_token = sign_state(_slim_state(result))
    return JSONResponse(content=_state_to_dict(result, req_id, new_token))


@app.post("/api/rag/search")
async def rag_search(request: Request):
    """BM25 runbook search — no LLM, no quota consumed."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body.")

    query       = str(body.get("query", ""))[:500]
    max_results = int(body.get("max_results", 5))
    max_results = min(max(max_results, 1), 20)

    if len(query) < 3:
        raise HTTPException(status_code=422, detail="Query must be at least 3 characters.")

    retriever = get_retriever()
    results   = retriever.search(query, max_results=max_results)
    return {"query": query, "results": results, "total_found": len(results)}


@app.post("/api/analyze/logs")
async def analyze_logs_endpoint(request: Request):
    """Static log-pattern analysis — no LLM, no quota consumed."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body.")

    raw_logs   = str(body.get("logs", ""))
    technology = str(body.get("technology", "unknown"))

    try:
        validate_text_input(raw_logs, settings.max_log_size, "logs")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    redacted = redact_secrets(raw_logs)
    result   = parse_logs(redacted, technology)
    return {
        "findings": result.get("findings", []),
        "summary":  result.get("summary", ""),
        "severity": result.get("severity", "low"),
    }


@app.post("/api/analyze/config")
async def analyze_config_endpoint(request: Request):
    """Static configuration analysis — no LLM, no quota consumed."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body.")

    raw_config = str(body.get("configuration", ""))
    cfg_type   = str(body.get("config_type", "")).lower()

    try:
        validate_text_input(raw_config, settings.max_config_size, "configuration")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    redacted = redact_secrets(raw_config)

    if cfg_type == "terraform":
        r = analyze_terraform(redacted)
    elif cfg_type == "kubernetes":
        r = analyze_kubernetes(redacted)
    elif cfg_type == "dockerfile":
        r = analyze_dockerfile(redacted)
    elif cfg_type in ("cicd", "github_actions", "gitlab_ci", "jenkins"):
        r = analyze_cicd(redacted, ci_type=cfg_type if cfg_type != "cicd" else "auto")
    else:
        r = {"findings": [], "summary": f"Unsupported config type: {cfg_type}", "severity": "low"}

    return {
        "findings": r.get("findings", []),
        "summary":  r.get("summary", ""),
        "severity": r.get("severity", "low"),
    }


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accept small plain-text files; return content as string. No storage."""
    try:
        validate_filename(file.filename or "unknown.txt")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    raw = await file.read(settings.max_upload_size + 1)
    if len(raw) > settings.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size} bytes. Use a smaller file.",
        )
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=422, detail="File must be UTF-8 plain text.")

    return {"filename": file.filename, "content": text, "size": len(raw)}
