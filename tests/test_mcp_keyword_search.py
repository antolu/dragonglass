from __future__ import annotations

import asyncio
import json
import types
from collections.abc import Callable
from typing import Self

import httpx
import pytest

import dragonglass.mcp.search as mcp_search
from dragonglass.config import Settings
from dragonglass.search.session import new_session


class FakeResponse:
    def __init__(
        self, status_code: int, payload: list[dict[str, object]] | dict[str, object]
    ) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> list[dict[str, object]] | dict[str, object]:
        return self._payload


class FakeAsyncClient:
    def __init__(
        self,
        response_for_url: Callable[[str, dict[str, object], str], FakeResponse],
        calls: list[tuple[str, dict[str, object], str]],
    ) -> None:
        self._response_for_url = response_for_url
        self._calls = calls

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        return None

    async def post(
        self,
        url: str,
        params: dict[str, object] | None = None,
        json_body: dict[str, object] | None = None,
    ) -> FakeResponse:
        payload = params if params is not None else json_body
        self._calls.append((url, payload or {}, "POST"))
        return self._response_for_url(url, payload or {}, "POST")


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    response_for_url: Callable[[str, dict[str, object], str], FakeResponse],
    calls: list[tuple[str, dict[str, object], str]],
) -> None:
    def factory(*args: object, **kwargs: object) -> FakeAsyncClient:
        return FakeAsyncClient(response_for_url=response_for_url, calls=calls)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_keyword_search_with_list_of_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        return FakeResponse(200, [{"filename": "Note1.md"}, {"filename": "Note2.md"}])

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    # Test with list of strings
    result = asyncio.run(
        mcp_search.create_search_server(settings).call_tool(
            "dragonglass_keyword_search", {"queries": ["query1", "query2"]}
        )
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 2  # noqa: PLR2004
    assert len(calls) == 2  # noqa: PLR2004
    assert calls[0][1]["query"] == "query1"
    assert calls[1][1]["query"] == "query2"


def test_keyword_search_with_single_string_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        return FakeResponse(200, [{"filename": "Note1.md"}])

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    # Test with single string for 'queries' (should be coerced by _coerce_json_string_to_list)
    result = asyncio.run(
        mcp_search.create_search_server(settings).call_tool(
            "dragonglass_keyword_search", {"queries": "query1"}
        )
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 1
    assert len(calls) == 1
    assert calls[0][1]["query"] == "query1"


def test_keyword_search_with_query_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        return FakeResponse(200, [{"filename": "Note1.md"}])

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    # Test with 'query' instead of 'queries'
    result = asyncio.run(
        mcp_search.create_search_server(settings).call_tool(
            "dragonglass_keyword_search", {"query": "query1"}
        )
    )
    data = json.loads(result.content[0].text)

    assert data["total_found"] == 1
    assert len(calls) == 1
    assert calls[0][1]["query"] == "query1"


def test_keyword_search_no_queries_error() -> None:
    new_session()
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.create_search_server(settings).call_tool(
            "dragonglass_keyword_search", {}
        )
    )
    data = json.loads(result.content[0].text)

    assert "error" in data
    assert "At least one search query is required" in data["error"]
