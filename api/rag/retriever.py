"""Singleton retriever facade over BM25RunbookIndex."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List

from api.rag.bm25_index import BM25RunbookIndex


@lru_cache(maxsize=1)
def get_retriever() -> BM25RunbookIndex:
    """Return the shared (lazily initialised) runbook index."""
    return BM25RunbookIndex()


def search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    return get_retriever().search(query, max_results=max_results)
