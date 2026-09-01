"""LangGraph workflow orchestrator – builds initial and continuation investigation graphs."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from api.workflow.state import InvestigationState

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END  # type: ignore[import]
    _LANGGRAPH_OK = True
except ImportError:
    _LANGGRAPH_OK = False
    logger.error("langgraph not installed — workflow will not function")


def _safe_node(agent_mod: Any, llm: Optional[Any]) -> Callable:
    """Wrap agent.run() so a single node failure never crashes the whole graph."""
    def node_fn(state: InvestigationState) -> Dict[str, Any]:
        try:
            return agent_mod.run(state, llm)
        except Exception as exc:
            logger.error(f"Node '{getattr(agent_mod,'AGENT_ROLE',agent_mod.__name__)}' error: {exc}", exc_info=True)
            msgs = list(state.get("agent_messages", []))
            msgs.append({
                "agent_name": getattr(agent_mod, "AGENT_ROLE", "unknown"),
                "phase":      getattr(agent_mod, "PHASE", "unknown"),
                "status":     "error",
                "message":    f"Non-fatal agent error: {str(exc)[:200]}",
                "timestamp":  datetime.now(timezone.utc).isoformat(),
            })
            return {
                "agent_messages": msgs,
                "errors": list(state.get("errors", [])) + [str(exc)],
            }
    return node_fn


def build_initial_graph(llm: Optional[Any]):
    """
    Full 8-node investigation graph (LangGraph orchestrates all agents):
      triage → plan → analyze → rag_search → root_cause → troubleshoot → safety_review → report

    LangChain/ChatGroq is used for LLM calls inside each node.
    CrewAI Agent objects define the specialist personas used in those calls.
    """
    if not _LANGGRAPH_OK:
        raise RuntimeError("langgraph is not installed. Run: pip install langgraph")

    from api.agents import (  # imported here to avoid circular imports at module load
        triage_agent, planner_agent, log_analysis_agent, rag_knowledge_agent,
        root_cause_agent, troubleshooting_agent, safety_reviewer_agent, report_agent,
    )

    g = StateGraph(InvestigationState)

    g.add_node("triage",        _safe_node(triage_agent,        llm))
    g.add_node("plan",          _safe_node(planner_agent,       llm))
    g.add_node("analyze",       _safe_node(log_analysis_agent,  llm))
    g.add_node("rag_search",    _safe_node(rag_knowledge_agent, llm))
    g.add_node("root_cause",    _safe_node(root_cause_agent,    llm))
    g.add_node("troubleshoot",  _safe_node(troubleshooting_agent, llm))
    g.add_node("safety_review", _safe_node(safety_reviewer_agent, llm))
    g.add_node("report",        _safe_node(report_agent,        llm))

    g.set_entry_point("triage")
    g.add_edge("triage",        "plan")
    g.add_edge("plan",          "analyze")
    g.add_edge("analyze",       "rag_search")
    g.add_edge("rag_search",    "root_cause")
    g.add_edge("root_cause",    "troubleshoot")
    g.add_edge("troubleshoot",  "safety_review")
    g.add_edge("safety_review", "report")
    g.add_edge("report",        END)

    return g.compile()


def build_continuation_graph(llm: Optional[Any]):
    """
    Continuation graph (triage + plan results reused from serialised state):
      analyze → rag_search → root_cause → troubleshoot → safety_review → report
    """
    if not _LANGGRAPH_OK:
        raise RuntimeError("langgraph is not installed.")

    from api.agents import (
        log_analysis_agent, rag_knowledge_agent, root_cause_agent,
        troubleshooting_agent, safety_reviewer_agent, report_agent,
    )

    g = StateGraph(InvestigationState)

    g.add_node("analyze",       _safe_node(log_analysis_agent,  llm))
    g.add_node("rag_search",    _safe_node(rag_knowledge_agent, llm))
    g.add_node("root_cause",    _safe_node(root_cause_agent,    llm))
    g.add_node("troubleshoot",  _safe_node(troubleshooting_agent, llm))
    g.add_node("safety_review", _safe_node(safety_reviewer_agent, llm))
    g.add_node("report",        _safe_node(report_agent,        llm))

    g.set_entry_point("analyze")
    g.add_edge("analyze",       "rag_search")
    g.add_edge("rag_search",    "root_cause")
    g.add_edge("root_cause",    "troubleshoot")
    g.add_edge("troubleshoot",  "safety_review")
    g.add_edge("safety_review", "report")
    g.add_edge("report",        END)

    return g.compile()
