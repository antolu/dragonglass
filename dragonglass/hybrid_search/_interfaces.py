from __future__ import annotations

import abc
import typing

from dragonglass.hybrid_search._types import SearchHit, SemanticResult


class KeywordSearchBackend(abc.ABC):
    @abc.abstractmethod
    async def keyword_search(self, queries: list[str]) -> list[SearchHit]: ...


class VectorSearchBackend(abc.ABC):
    @abc.abstractmethod
    async def vector_search(
        self,
        query: str,
        *,
        top_n: int = 10,
        min_score: float = 0.35,
        allowlist: list[str] | None = None,
    ) -> list[SearchHit]: ...


class LLMCompletionFn(typing.Protocol):
    async def __call__(
        self,
        messages: list[dict[str, str]],
        *,
        system: str | None = None,
    ) -> str: ...


class SemanticSearchBackend(abc.ABC):
    @abc.abstractmethod
    async def semantic_search(  # noqa: PLR0913
        self,
        query: str,
        *,
        keyword_backend: KeywordSearchBackend | None = None,
        vector_backend: VectorSearchBackend | None = None,
        llm: LLMCompletionFn | None = None,
        system_prompt: str | None = None,
        top_n: int = 10,
    ) -> list[SemanticResult]: ...
