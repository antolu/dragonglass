from __future__ import annotations

import asyncio
import types
from collections.abc import Callable
from typing import Self

import httpx
import pytest

import dragonglass.mcp.edit as mcp_search
from dragonglass.config import Settings
from dragonglass.search.session import new_session


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
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

    async def get(self, url: str, params: dict[str, object]) -> FakeResponse:
        self._calls.append((url, params, "GET"))
        return self._response_for_url(url, params, "GET")

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self._calls.append((url, json, "POST"))
        return self._response_for_url(url, json, "POST")

    async def patch(self, url: str, json: dict[str, object]) -> FakeResponse:
        self._calls.append((url, json, "PATCH"))
        return self._response_for_url(url, json, "PATCH")


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    response_for_url: Callable[[str, dict[str, object], str], FakeResponse],
    calls: list[tuple[str, dict[str, object], str]],
) -> None:
    def factory(*args: object, **kwargs: object) -> FakeAsyncClient:
        return FakeAsyncClient(response_for_url=response_for_url, calls=calls)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_read_note_with_hash_stores_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    session = new_session()
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, params: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "GET"
        assert url.endswith("/notes/read")
        assert params == {"path": "Notes/Test.md"}
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "content": "hello",
                "line_count": 1,
                "content_hash": "sha256:oldhash",
                "mtime": 1,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(mcp_search.do_read_note_with_hash(settings, "Notes/Test.md"))

    assert result["content_hash"] == "sha256:oldhash"
    assert session.get_last_read_hash("Notes/Test.md") == "sha256:oldhash"
    assert result["content_with_line_numbers"] == "L1: hello"
    assert result["total_lines"] == 1
    assert len(calls) == 1
    assert calls[0][2] == "GET"


def test_read_note_with_hash_line_numbers_and_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = new_session()
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, params: dict[str, object], method: str
    ) -> FakeResponse:
        return FakeResponse(
            200,
            {
                "path": "Notes/Range.md",
                "content": "line1\nline2\nline3\nline4",
                "line_count": 4,
                "content_hash": "sha256:fullhash",
                "mtime": 1,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    # Read specific range: lines 2 to 3
    result = asyncio.run(
        mcp_search.do_read_note_with_hash(
            settings, "Notes/Range.md", start_line=2, end_line=3
        )
    )

    assert result["content_hash"] == "sha256:fullhash"
    assert session.get_last_read_hash("Notes/Range.md") == "sha256:fullhash"
    # Should only show L2 and L3
    assert result["content_with_line_numbers"] == "L2: line2\nL3: line3"
    expected_total_lines = 4
    assert result["total_lines"] == expected_total_lines


def test_patch_note_lines_requires_previous_hash() -> None:
    new_session()
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_patch_note_lines(
            settings,
            {
                "path": "Notes/Test.md",
                "start_line": 1,
                "end_line": 1,
                "replacement": "updated",
                "expected_hash": None,
            },
        )
    )

    assert "No stored hash for this file" in str(result.get("error", ""))


def test_patch_note_lines_uses_stored_hash_when_expected_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = new_session()
    session.set_last_read_hash("Notes/Test.md", "sha256:storedhash")
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "PATCH"
        assert url.endswith("/notes/patch-lines")
        assert payload["expected_hash"] == "sha256:storedhash"
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "applied_start_line": 2,
                "applied_end_line": 2,
                "new_hash": "sha256:newhash",
                "new_line_count": 3,
                "mtime": 2,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_patch_note_lines(
            settings,
            {
                "path": "Notes/Test.md",
                "start_line": 2,
                "end_line": 2,
                "replacement": "patched",
                "expected_hash": None,
            },
        )
    )

    assert result["new_hash"] == "sha256:newhash"
    assert session.get_last_read_hash("Notes/Test.md") == "sha256:newhash"
    assert len(calls) == 1
    assert calls[0][2] == "PATCH"


def test_patch_note_lines_propagates_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = new_session()
    session.set_last_read_hash("Notes/Test.md", "sha256:stalehash")
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "PATCH"
        assert url.endswith("/notes/patch-lines")
        return FakeResponse(
            409,
            {
                "error": "hash_mismatch",
                "path": "Notes/Test.md",
                "expected_hash": payload["expected_hash"],
                "current_hash": "sha256:currenthash",
                "mtime": 3,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_patch_note_lines(
            settings,
            {
                "path": "Notes/Test.md",
                "start_line": 1,
                "end_line": 1,
                "replacement": "patched",
                "expected_hash": None,
            },
        )
    )

    assert "modified since it was last read" in str(result["error"])
    assert session.get_last_read_hash("Notes/Test.md") == "sha256:stalehash"


def test_patch_note_lines_explicit_expected_hash_overrides_stored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = new_session()
    session.set_last_read_hash("Notes/Test.md", "sha256:storedhash")
    calls: list[tuple[str, dict[str, object], str]] = []

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "PATCH"
        assert url.endswith("/notes/patch-lines")
        assert payload["expected_hash"] == "sha256:explicit"
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "applied_start_line": 1,
                "applied_end_line": 1,
                "new_hash": "sha256:afterexplicit",
                "new_line_count": 1,
                "mtime": 4,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_patch_note_lines(
            settings,
            {
                "path": "Notes/Test.md",
                "start_line": 1,
                "end_line": 1,
                "replacement": "patched",
                "expected_hash": "sha256:explicit",
            },
        )
    )

    assert result["new_hash"] == "sha256:afterexplicit"
    assert session.get_last_read_hash("Notes/Test.md") == "sha256:afterexplicit"
