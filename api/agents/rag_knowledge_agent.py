"""RAG Knowledge Agent – searches bundled runbooks; never fabricates sources."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from api.core.logging_config import get_logger
from api.providers.llm_provider import invoke_with_retry

logger = get_logger(__name__)

AGENT_ROLE = "Knowledge Base Research Specialist"
AGENT_GOAL = "Search bundled DevOps runbooks and return only real, cited sources that are relevant to the current issue"
AGENT_BACKSTORY = (
    "You are a technical knowledge manager who maintains and curates an extensive DevOps runbook library. "
    "You are trained to retrieve only real, documented knowledge — you never invent sources, "
    "misattribute content, or fabricate citations."
)
PHASE = "rag_search"

try:
    from crewai import Agent as CrewAIAgent  # type: ignore[import]
    _CREWAI_AVAILABLE = True
except ImportError:
    CrewAIAgent = None
    _CREWAI_AVAILABLE = False


def _msg(status: str, message: str) -> Dict[str, Any]:
    return {"agent_name": AGENT_ROLE, "phase": PHASE, "status": status,
            "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}


def _get_persona(llm=None):
    if _CREWAI_AVAILABLE:
        try:
            kw: Dict[str, Any] = {"role": AGENT_ROLE, "goal": AGENT_GOAL, "backstory": AGENT_BACKSTORY,
                                   "allow_delegation": False, "verbose": False}
            if llm is not None:
                kw["llm"] = llm
            a = CrewAIAgent(**kw)
            return a.role, a.goal, a.backstory
        except Exception as e:
            logger.debug(f"CrewAI rag-agent: {e}")
    return AGENT_ROLE, AGENT_GOAL, AGENT_BACKSTORY


def _build_query(state: dict) -> str:
    """Build BM25 search query from triage findings."""
    parts = [
        state.get("issue_category", ""),
        " ".join(state.get("error_codes", [])[:5]),
        " ".join(state.get("affected_services", [])[:4]),
        (state.get("triage_summary", ""))[:200],
        (state.get("problem_description", ""))[:200],
    ]
    return " ".join(p for p in parts if p).strip()[:500]


def run(state: dict, llm: Optional[BaseChatModel]) -> dict:
    """LangGraph node: RAG knowledge agent."""
    from api.rag.retriever import get_retriever  # lazy import

    msgs: List[Dict[str, Any]] = list(state.get("agent_messages", []))
    msgs.append(_msg("running", "RAG Knowledge Agent: searching runbooks…"))

    retriever = get_retriever()
    if not retriever.is_ready:
        msgs.append(_msg("complete", "Runbook index not ready — no citations available."))
        return {"agent_messages": msgs, "current_phase": "rag_complete", "runbook_citations": []}

    query = _build_query(state)
    if not query:
        msgs.append(_msg("complete", "No query — skipping runbook search."))
        return {"agent_messages": msgs, "current_phase": "rag_complete", "runbook_citations": []}

    # BM25 search — primary retrieval (no LLM needed)
    raw = retriever.search(query, max_results=10)
    msgs.append(_msg("running", f"BM25 search returned {len(raw)} candidate sections."))

    if not raw:
        msgs.append(_msg("complete", "No matching runbook sections found."))
        return {"agent_messages": msgs, "current_phase": "rag_complete", "runbook_citations": []}

    # Optional LLM re-ranking / filtering
    if llm is not None and raw:
        role, goal, backstory = _get_persona(llm)
        candidates = "\n".join(
            f"{i+1}. [{r['filename']} — {r['section']}] score={r['relevance_score']:.2f}\n   {r['snippet'][:200]}"
            for i, r in enumerate(raw)
        )
        system = f"""You are a {role}. Goal: {goal}
Background: {backstory}

You are given BM25 search results (real filenames and sections). Select the 5 most relevant ones
for the current issue. Return ONLY valid JSON:
{{"selected_indices": [0, 1, 2, 3, 4]}}  (0-based indices, max 5)
IMPORTANT: Only use the indices provided. Do NOT invent filenames or sections."""

        human = (
            f"Issue: {state.get('issue_category','?')} — {state.get('triage_summary','')[:200]}\n"
            f"Error codes: {', '.join(state.get('error_codes',[]))}\n\n"
            f"Candidates:\n{candidates}"
        )

        try:
            resp = invoke_with_retry(llm, [SystemMessage(content=system), HumanMessage(content=human)])
            result = _extract_json(resp.content if hasattr(resp, "content") else str(resp))
            indices = result.get("selected_indices", [])
            if isinstance(indices, list) and indices:
                valid = [raw[i] for i in indices if isinstance(i, int) and 0 <= i < len(raw)]
                if valid:
                    raw = valid
        except Exception as exc:
            logger.warning(f"RAG LLM re-ranking error (non-fatal): {exc}")

    citations = raw[:6]  # cap at 6
    msgs.append(_msg("complete", f"Selected {len(citations)} runbook citation(s): "
                     + ", ".join(f"{c['filename']}§{c['section']}" for c in citations[:3])))
    return {"agent_messages": msgs, "current_phase": "rag_complete", "runbook_citations": citations}
