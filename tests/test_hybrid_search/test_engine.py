from __future__ import annotations

import asyncio

import pytest

from dragonglass.hybrid_search import (
    KeywordHit,
    KeywordSearchBackend,
    LLMCompletionFn,
    SearchEngine,
    SemanticResult,
    SemanticSearchBackend,
    VectorHit,
    VectorSearchBackend,
)


class MockKeywordBackend(KeywordSearchBackend):
    def __init__(self, hits: list[KeywordHit]) -> None:
        self.hits = hits
        self.calls: list[list[str]] = []

    async def keyword_search(self, queries: list[str]) -> list[KeywordHit]:
        self.calls.append(queries)
        return self.hits


class MockVectorBackend(VectorSearchBackend):
    def __init__(self, hits: list[VectorHit]) -> None:
        self.hits = hits
        self.last_call: dict[str, object] = {}

    async def vector_search(
        self,
        query: str,
        *,
        top_n: int = 10,
        min_score: float = 0.35,
        allowlist: list[str] | None = None,
    ) -> list[VectorHit]:
        self.last_call = {
            "query": query,
            "top_n": top_n,
            "min_score": min_score,
            "allowlist": allowlist,
        }
        return self.hits


class MockSemanticBackend(SemanticSearchBackend):
    def __init__(self, results: list[SemanticResult]) -> None:
        self.results = results
        self.last_call: dict[str, object] = {}

    async def semantic_search(  # noqa: PLR0913
        self,
        query: str,
        *,
        keyword_backend: KeywordSearchBackend | None = None,
        vector_backend: VectorSearchBackend | None = None,
        llm: LLMCompletionFn | None = None,
        system_prompt: str | None = None,
        top_n: int = 10,
    ) -> list[SemanticResult]:
        self.last_call = {
            "query": query,
            "keyword_backend": keyword_backend,
            "vector_backend": vector_backend,
            "llm": llm,
            "system_prompt": system_prompt,
            "top_n": top_n,
        }
        return self.results


def test_keyword_search_delegates_to_backend() -> None:
    backend = MockKeywordBackend([KeywordHit(path="a.md"), KeywordHit(path="b.md")])
    engine = SearchEngine(keyword_backend=backend)
    engine.new_session()
    hits = asyncio.run(engine.keyword_search(["foo", "bar"]))
    assert len(hits) == 2  # noqa: PLR2004
    assert hits[0].path == "a.md"
    assert backend.calls == [["foo", "bar"]]


def test_keyword_search_updates_session() -> None:
    backend = MockKeywordBackend([KeywordHit(path="note.md")])
    engine = SearchEngine(keyword_backend=backend)
    engine.new_session()
    asyncio.run(engine.keyword_search(["query"]))
    assert engine.session is not None
    assert "note.md" in engine.session.file_paths


def test_keyword_search_no_backend_raises() -> None:
    engine = SearchEngine()
    engine.new_session()
    with pytest.raises(RuntimeError, match="No keyword search backend"):
        asyncio.run(engine.keyword_search(["query"]))


def test_vector_search_delegates_to_backend() -> None:
    backend = MockVectorBackend([VectorHit(path="x.md", score=0.7)])
    engine = SearchEngine(vector_backend=backend)
    engine.new_session()
    hits = asyncio.run(engine.vector_search("meaning", top_n=5, min_score=0.4))
    assert len(hits) == 1
    assert hits[0].path == "x.md"


def test_vector_search_no_backend_raises() -> None:
    engine = SearchEngine()
    engine.new_session()
    with pytest.raises(RuntimeError, match="No vector search backend"):
        asyncio.run(engine.vector_search("query"))


def test_vector_search_uses_allowlist_from_session() -> None:
    kw_backend = MockKeywordBackend([KeywordHit(path="a.md"), KeywordHit(path="b.md")])
    vec_backend = MockVectorBackend([VectorHit(path="a.md", score=0.8)])
    engine = SearchEngine(keyword_backend=kw_backend, vector_backend=vec_backend)
    engine.new_session()
    asyncio.run(engine.keyword_search(["query"]))
    asyncio.run(engine.vector_search("meaning"))
    assert vec_backend.last_call["allowlist"] == ["a.md", "b.md"]


def test_vector_search_bumps_min_score_with_allowlist() -> None:
    kw_backend = MockKeywordBackend([KeywordHit(path="a.md")])
    vec_backend = MockVectorBackend([])
    engine = SearchEngine(keyword_backend=kw_backend, vector_backend=vec_backend)
    engine.new_session()
    asyncio.run(engine.keyword_search(["query"]))
    asyncio.run(engine.vector_search("meaning", min_score=0.3))
    assert vec_backend.last_call["min_score"] == pytest.approx(0.5)


def test_vector_search_no_allowlist_uses_provided_min_score() -> None:
    vec_backend = MockVectorBackend([])
    engine = SearchEngine(vector_backend=vec_backend)
    engine.new_session()
    asyncio.run(engine.vector_search("meaning", min_score=0.3))
    assert vec_backend.last_call["min_score"] == pytest.approx(0.3)
    assert vec_backend.last_call["allowlist"] is None


def test_semantic_search_passes_backends_and_llm() -> None:
    kw_backend = MockKeywordBackend([])
    vec_backend = MockVectorBackend([])
    sem_backend = MockSemanticBackend([SemanticResult(path="r.md", score=0.9)])

    async def my_llm(  # noqa: RUF029
        messages: list[dict[str, str]], *, system: str | None = None
    ) -> str:
        return "response"

    engine = SearchEngine(
        keyword_backend=kw_backend,
        vector_backend=vec_backend,
        semantic_backend=sem_backend,
        llm=my_llm,
    )
    engine.new_session()
    results = asyncio.run(
        engine.semantic_search("query", system_prompt="be concise", top_n=3)
    )
    assert len(results) == 1
    assert results[0].path == "r.md"
    assert sem_backend.last_call["keyword_backend"] is kw_backend
    assert sem_backend.last_call["vector_backend"] is vec_backend
    assert sem_backend.last_call["llm"] is my_llm
    assert sem_backend.last_call["system_prompt"] == "be concise"
    assert sem_backend.last_call["top_n"] == 3  # noqa: PLR2004


def test_semantic_search_no_backend_raises() -> None:
    engine = SearchEngine()
    engine.new_session()
    with pytest.raises(RuntimeError, match="No semantic search backend"):
        asyncio.run(engine.semantic_search("query"))


def test_new_session_creates_session() -> None:
    engine = SearchEngine()
    assert engine.session is None
    session = engine.new_session()
    assert engine.session is session
    assert session.id is not None


def test_new_session_replaces_previous() -> None:
    engine = SearchEngine()
    s1 = engine.new_session()
    s2 = engine.new_session()
    assert s1 is not s2
    assert engine.session is s2
