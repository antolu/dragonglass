from __future__ import annotations

import logging

from dragonglass.hybrid_search._interfaces import (
    KeywordSearchBackend,
    LLMCompletionFn,
    SemanticSearchBackend,
    VectorSearchBackend,
)
from dragonglass.hybrid_search._session import SearchSession
from dragonglass.hybrid_search._types import KeywordHit, SemanticResult, VectorHit

logger = logging.getLogger(__name__)

_ALLOWLIST_MIN_SCORE = 0.5


class SearchEngine:
    def __init__(
        self,
        *,
        keyword_backend: KeywordSearchBackend | None = None,
        vector_backend: VectorSearchBackend | None = None,
        semantic_backend: SemanticSearchBackend | None = None,
        llm: LLMCompletionFn | None = None,
    ) -> None:
        self._keyword_backend = keyword_backend
        self._vector_backend = vector_backend
        self._semantic_backend = semantic_backend
        self._llm = llm
        self._session: SearchSession | None = None

    def new_session(self) -> SearchSession:
        self._session = SearchSession()
        logger.info("search engine new_session id=%s", self._session.id)
        return self._session

    @property
    def session(self) -> SearchSession | None:
        return self._session

    async def keyword_search(self, queries: list[str]) -> list[KeywordHit]:
        if self._keyword_backend is None:
            raise RuntimeError("No keyword search backend configured")
        hits = await self._keyword_backend.keyword_search(queries)
        if self._session is not None:
            self._session.add_keyword_results([h.path for h in hits])
        return hits

    async def vector_search(
        self,
        query: str,
        *,
        top_n: int = 10,
        min_score: float = 0.35,
    ) -> list[VectorHit]:
        if self._vector_backend is None:
            raise RuntimeError("No vector search backend configured")
        allowlist = self._session.allowlist if self._session else None
        effective_min = _ALLOWLIST_MIN_SCORE if allowlist else min_score
        logger.debug(
            "vector_search query=%r top_n=%d min_score=%.2f allowlist=%d",
            query,
            top_n,
            effective_min,
            len(allowlist) if allowlist else 0,
        )
        return await self._vector_backend.vector_search(
            query,
            top_n=top_n,
            min_score=effective_min,
            allowlist=allowlist or None,
        )

    async def semantic_search(
        self,
        query: str,
        *,
        system_prompt: str | None = None,
        top_n: int = 10,
    ) -> list[SemanticResult]:
        if self._semantic_backend is None:
            raise RuntimeError("No semantic search backend configured")
        return await self._semantic_backend.semantic_search(
            query,
            keyword_backend=self._keyword_backend,
            vector_backend=self._vector_backend,
            llm=self._llm,
            system_prompt=system_prompt,
            top_n=top_n,
        )
