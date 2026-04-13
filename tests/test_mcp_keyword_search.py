from __future__ import annotations

import asyncio
import json
import sys

import fastmcp

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

import dragonglass.mcp.search as mcp_search
from dragonglass.config import Settings
from dragonglass.hybrid_search import (
    KeywordSearchBackend,
    SearchEngine,
    SearchHit,
    VectorSearchBackend,
)


class MockObsidianBackend(KeywordSearchBackend, VectorSearchBackend):
    def __init__(self, keyword_hits: list[SearchHit]) -> None:
        self._keyword_hits = keyword_hits
        self.keyword_calls: list[list[str]] = []

    @override
    async def keyword_search(self, queries: list[str]) -> list[SearchHit]:
        self.keyword_calls.append(queries)
        return self._keyword_hits

    @override
    async def vector_search(
        self,
        query: str,
        *,
        top_n: int = 10,
        min_score: float = 0.35,
        allowlist: list[str] | None = None,
    ) -> list[SearchHit]:
        return []


def _make_server(hits: list[SearchHit]) -> tuple[fastmcp.FastMCP, MockObsidianBackend]:
    backend = MockObsidianBackend(hits)
    engine = SearchEngine(keyword_backend=backend, vector_backend=backend)
    settings = Settings(vector_search_url="http://vector.local")
    server = mcp_search.create_search_server(engine, settings)
    asyncio.run(server.call_tool("dragonglass_new_search_session", {}))
    return server, backend


def test_keyword_search_with_list_of_queries() -> None:
    server, backend = _make_server([
        SearchHit(path="Note1.md"),
        SearchHit(path="Note2.md"),
    ])

    result = asyncio.run(
        server.call_tool(
            "dragonglass_keyword_search", {"queries": ["query1", "query2"]}
        )
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 2  # noqa: PLR2004
    assert backend.keyword_calls == [["query1", "query2"]]


def test_keyword_search_with_single_string_queries() -> None:
    server, backend = _make_server([SearchHit(path="Note1.md")])

    result = asyncio.run(
        server.call_tool("dragonglass_keyword_search", {"queries": "query1"})
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 1
    assert backend.keyword_calls == [["query1"]]


def test_keyword_search_with_query_alias() -> None:
    server, backend = _make_server([SearchHit(path="Note1.md")])

    result = asyncio.run(
        server.call_tool("dragonglass_keyword_search", {"query": "query1"})
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 1
    assert backend.keyword_calls == [["query1"]]


def test_keyword_search_preview_paths() -> None:
    server, _ = _make_server([
        SearchHit(path="Note1.md"),
        SearchHit(path="Note2.md"),
    ])

    result = asyncio.run(
        server.call_tool("dragonglass_keyword_search", {"queries": ["q"]})
    )
    data = json.loads(result.content[0].text)

    assert "preview_paths" in data
    assert "Note1.md" in data["preview_paths"]
    assert "Note2.md" in data["preview_paths"]


def test_keyword_search_no_queries_error() -> None:
    server, _ = _make_server([])

    result = asyncio.run(server.call_tool("dragonglass_keyword_search", {}))
    data = json.loads(result.content[0].text)

    assert "error" in data
    assert "At least one search query is required" in data["error"]


def test_keyword_search_no_session_error() -> None:
    backend = MockObsidianBackend([])
    engine = SearchEngine(keyword_backend=backend)
    settings = Settings(vector_search_url="http://vector.local")
    server = mcp_search.create_search_server(engine, settings)

    result = asyncio.run(
        server.call_tool("dragonglass_keyword_search", {"queries": ["q"]})
    )
    data = json.loads(result.content[0].text)

    assert "error" in data
    assert "dragonglass_new_search_session" in data["error"]
