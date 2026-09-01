"""MCP-compatible tool: runbook search (delegates to RAG retriever)."""
from __future__ import annotations

from typing import Any, Dict, List


def search_runbooks(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    MCP-compatible stateless tool: search bundled DevOps runbooks.
    Returns citations with real filename, section and snippet.
    Never fabricates sources.
    """
    from api.rag.retriever import get_retriever  # lazy import avoids circular deps
    retriever = get_retriever()
    return retriever.search(query, max_results=max_results)
