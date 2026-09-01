"""BM25 keyword index over bundled Markdown runbooks. No embedding API required."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rank_bm25 import BM25Okapi  # type: ignore
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False

# ── Path resolution ───────────────────────────────────────────────────────────
_MODULE_DIR = Path(__file__).resolve().parent          # api/rag/
_PROJECT_ROOT = _MODULE_DIR.parent.parent               # project root
_DEFAULT_RUNBOOKS_DIR = _PROJECT_ROOT / "runbooks"


def _resolve_runbooks_path() -> Path:
    """Find the runbooks directory, trying several candidate locations."""
    from api.core.config import get_settings
    try:
        cfg_path = Path(get_settings().runbooks_path)
        if not cfg_path.is_absolute():
            cfg_path = _PROJECT_ROOT / cfg_path
        if cfg_path.exists():
            return cfg_path
    except Exception:
        pass

    if _DEFAULT_RUNBOOKS_DIR.exists():
        return _DEFAULT_RUNBOOKS_DIR

    # Vercel: try relative to CWD
    cwd_path = Path.cwd() / "runbooks"
    if cwd_path.exists():
        return cwd_path

    return _DEFAULT_RUNBOOKS_DIR   # may not exist; handled gracefully


# ── Tokenisation ──────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class RunbookChunk:
    filename: str
    section: str
    content: str
    tokens: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        combined = f"{self.filename} {self.section} {self.content}"
        self.tokens = _tokenize(combined)


# ── Index ─────────────────────────────────────────────────────────────────────
class BM25RunbookIndex:
    """
    Builds a BM25Okapi index over runbook sections.
    Loaded once at startup; all searches are read-only and stateless.
    """

    def __init__(self, runbooks_dir: Optional[Path] = None) -> None:
        self._dir = runbooks_dir or _resolve_runbooks_path()
        self._chunks: List[RunbookChunk] = []
        self._bm25: Optional[Any] = None
        self._load()

    # ── Loading & parsing ─────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._dir.exists():
            return
        for md_file in sorted(self._dir.glob("*.md")):
            self._parse_file(md_file)
        self._build_index()

    def _parse_file(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        filename = path.name
        # Split on H1/H2/H3 headings, keeping the heading line
        parts = re.split(r"(?m)^(?=#{1,3} )", text)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = part.splitlines()
            if lines[0].startswith("#"):
                heading = lines[0].lstrip("#").strip()
                body = "\n".join(lines[1:]).strip()
            else:
                heading = "Overview"
                body = part

            if len(body) < 20:
                continue   # skip trivially empty sections

            self._chunks.append(RunbookChunk(
                filename=filename,
                section=heading,
                content=body,
            ))

    def _build_index(self) -> None:
        if not self._chunks or not _BM25_AVAILABLE:
            return
        corpus = [c.tokens for c in self._chunks]
        self._bm25 = BM25Okapi(corpus)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Return top-k matching chunks with real filename, section, relevance score,
        and a text snippet.  Never fabricates sources.
        """
        if not query or not self._chunks:
            return []

        if not _BM25_AVAILABLE or self._bm25 is None:
            # Graceful fallback: keyword-contains scan
            return self._keyword_fallback(query, max_results)

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results: List[Dict[str, Any]] = []
        seen_files: set[str] = set()

        for idx in ranked:
            if len(results) >= max_results:
                break
            score = float(scores[idx])
            if score <= 0:
                break

            chunk = self._chunks[idx]
            # Deduplicate: show at most 2 sections per file
            file_key = f"{chunk.filename}:{chunk.section}"
            if file_key in seen_files:
                continue
            seen_files.add(file_key)

            snippet = chunk.content[:400].replace("\n", " ").strip()
            if len(chunk.content) > 400:
                snippet += "…"

            # Normalise score to 0-1 range (BM25 has no fixed upper bound)
            normalised = min(score / max(scores) if max(scores) > 0 else 0, 1.0)

            results.append({
                "filename": chunk.filename,
                "section": chunk.section,
                "relevance_score": round(normalised, 3),
                "snippet": snippet,
            })

        return results

    def _keyword_fallback(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Simple substring search when BM25 is unavailable."""
        terms = _tokenize(query)
        scored: List[tuple[int, float, RunbookChunk]] = []

        for chunk in self._chunks:
            hits = sum(1 for t in terms if t in chunk.tokens)
            if hits:
                scored.append((hits, len(chunk.tokens), chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for hits, _, chunk in scored[:max_results]:
            snippet = chunk.content[:400].replace("\n", " ").strip()
            results.append({
                "filename": chunk.filename,
                "section": chunk.section,
                "relevance_score": round(hits / max(len(_tokenize(query)), 1), 3),
                "snippet": snippet,
            })
        return results

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def is_ready(self) -> bool:
        return len(self._chunks) > 0
