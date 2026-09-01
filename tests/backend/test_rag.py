"""Tests for BM25 RAG retrieval – no LLM calls, no API quota."""
from __future__ import annotations
import pytest
from pathlib import Path
from api.rag.bm25_index import BM25RunbookIndex
from api.rag.retriever  import get_retriever


class TestBM25Index:
    @pytest.fixture
    def index(self):
        # Point at the real runbooks directory
        runbooks_dir = Path(__file__).parent.parent.parent / "runbooks"
        return BM25RunbookIndex(runbooks_dir=runbooks_dir)

    def test_index_loads_runbooks(self, index):
        assert index.chunk_count > 0, "BM25 index should have at least 1 chunk"

    def test_kubernetes_query_returns_results(self, index):
        results = index.search("kubernetes crashloopbackoff oomkilled", max_results=5)
        assert len(results) > 0

    def test_results_have_real_filenames(self, index):
        results = index.search("terraform state lock", max_results=3)
        for r in results:
            assert r["filename"].endswith(".md"), "Citations must point to real .md files"
            assert "section" in r
            assert 0.0 <= r["relevance_score"] <= 1.0

    def test_no_fabricated_sources(self, index):
        """Search results must only reference files that exist on disk."""
        runbooks_dir = Path(__file__).parent.parent.parent / "runbooks"
        real_files = {f.name for f in runbooks_dir.glob("*.md")}
        results = index.search("docker build failure", max_results=10)
        for r in results:
            assert r["filename"] in real_files, (
                f"Fabricated citation detected: {r['filename']} not in {real_files}"
            )

    def test_empty_query_returns_empty(self, index):
        results = index.search("", max_results=5)
        assert results == []

    def test_irrelevant_query_low_or_no_results(self, index):
        # Should not hallucinate results for nonsense
        results = index.search("xyzzy frobnicator quux", max_results=5)
        # May return 0 or low-scoring results — just ensure no crash
        assert isinstance(results, list)

    def test_max_results_respected(self, index):
        results = index.search("kubernetes pod failure", max_results=2)
        assert len(results) <= 2

    def test_snippet_is_string(self, index):
        results = index.search("SSL certificate expired", max_results=3)
        for r in results:
            assert isinstance(r.get("snippet", ""), str)


class TestRetrieverSingleton:
    def test_get_retriever_returns_same_instance(self):
        r1 = get_retriever()
        r2 = get_retriever()
        assert r1 is r2

    def test_retriever_is_ready(self):
        r = get_retriever()
        assert r.is_ready

    def test_retriever_search_works(self):
        r = get_retriever()
        results = r.search("kubernetes crashloopbackoff", max_results=3)
        assert isinstance(results, list)
