from __future__ import annotations

import logging
import typing

import httpx
from pydantic import JsonValue

from dragonglass.hybrid_search import (
    KeywordSearchBackend,
    SearchHit,
    VectorSearchBackend,
)

logger = logging.getLogger(__name__)


class ObsidianHttpBackend(KeywordSearchBackend, VectorSearchBackend):
    def __init__(
        self,
        base_url: str,
        keyword_timeout: float = 10.0,
        vector_timeout: float = 15.0,
    ) -> None:
        self._base_url = base_url
        self._keyword_timeout = keyword_timeout
        self._vector_timeout = vector_timeout

    async def _keyword_search_one(
        self, client: httpx.AsyncClient, query: str, seen: set[str]
    ) -> list[SearchHit]:
        try:
            resp = await client.post(
                f"{self._base_url}/search/simple/",
                params={"query": query, "contextLength": 0},
            )
            logger.debug("keyword_search query=%r status=%d", query, resp.status_code)
            if resp.status_code == httpx.codes.OK:
                return [
                    SearchHit(path=r["filename"])
                    for r in resp.json()
                    if r.get("filename") and r["filename"] not in seen
                ]
        except Exception:
            logger.exception("keyword search failed for query %r", query)
        return []

    async def keyword_search(self, queries: list[str]) -> list[SearchHit]:
        hits: list[SearchHit] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(
            timeout=self._keyword_timeout, verify=False
        ) as client:
            for query in queries:
                for hit in await self._keyword_search_one(client, query, seen):
                    seen.add(hit.path)
                    hits.append(hit)
        return hits

    async def vector_search(
        self,
        query: str,
        *,
        top_n: int = 10,
        min_score: float = 0.35,
        allowlist: list[str] | None = None,
    ) -> list[SearchHit]:
        payload: dict[str, JsonValue] = {
            "text": query,
            "top_n": top_n,
            "min_score": min_score,
        }
        if allowlist:
            payload["allowlist"] = typing.cast(JsonValue, allowlist)
        try:
            async with httpx.AsyncClient(timeout=self._vector_timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/search/text",
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
                results = body.get("results", []) if isinstance(body, dict) else []
                hits: list[SearchHit] = []
                for r in results:
                    if not isinstance(r, dict):
                        continue
                    score_raw = r.get("score")
                    if not isinstance(score_raw, int | float):
                        continue
                    score = float(score_raw)
                    if score < min_score:
                        continue
                    path = r.get("path", "")
                    if isinstance(path, str):
                        hits.append(SearchHit(path=path, score=score))
                logger.debug(
                    "vector_search returned=%d after_filter=%d",
                    len(results),
                    len(hits),
                )
                return hits
        except Exception:
            logger.exception("vector search failed")
            return []
