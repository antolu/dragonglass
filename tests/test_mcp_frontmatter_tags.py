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

_EXPECTED_PATCH_CALLS = 2
_EXPECTED_END_LINE = 6


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


def test_manage_frontmatter_get_returns_existing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = "---\ntitle: Note\nstatus: active\n---\n\nBody"

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "GET"
        assert url.endswith("/notes/read")
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "content": note_content,
                "content_hash": "sha256:hash0",
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_frontmatter(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "get",
                "key": "status",
            },
        )
    )

    assert result["exists"] is True
    assert result["value"] == "active"
    assert len(calls) == 1


def test_manage_frontmatter_set_updates_entire_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = "---\ntitle: Note\nstatus: active\n---\n\nBody"

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        if method == "GET":
            return FakeResponse(
                200,
                {
                    "path": "Notes/Test.md",
                    "content": note_content,
                    "content_hash": "sha256:hash0",
                },
            )
        assert method == "PATCH"
        assert url.endswith("/notes/patch-lines")
        assert payload["expected_hash"] == "sha256:hash0"
        assert payload["start_line"] == 1
        assert payload["end_line"] == _EXPECTED_END_LINE
        replacement = str(payload["replacement"])
        assert "status: done" in replacement
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "new_hash": "sha256:hash1",
                "new_line_count": 6,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_frontmatter(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "set",
                "key": "status",
                "value": "done",
            },
        )
    )

    assert result["value"] == "done"
    assert len(calls) == _EXPECTED_PATCH_CALLS


def test_manage_tags_add_updates_frontmatter_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = "---\ntitle: Note\ntags:\n  - project\n---\n\nBody #inline"

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        if method == "GET":
            return FakeResponse(
                200,
                {
                    "path": "Notes/Test.md",
                    "content": note_content,
                    "content_hash": "sha256:hash0",
                },
            )
        assert method == "PATCH"
        replacement = str(payload["replacement"])
        assert "  - project" in replacement
        assert "  - active" in replacement
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "new_hash": "sha256:hash1",
                "new_line_count": 6,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_tags(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "add",
                "tags": ["#active", "project"],
            },
        )
    )

    assert result["added"] == ["active"]
    assert "active" in str(result["tags"])
    assert len(calls) == _EXPECTED_PATCH_CALLS


def test_manage_tags_remove_removes_frontmatter_and_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = (
        "---\ntitle: Note\ntags:\n  - project\n  - active\n---\n"
        "\nTask #active and #keep"
    )

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        if method == "GET":
            return FakeResponse(
                200,
                {
                    "path": "Notes/Test.md",
                    "content": note_content,
                    "content_hash": "sha256:hash0",
                },
            )
        assert method == "PATCH"
        replacement = str(payload["replacement"])
        assert "  - active" not in replacement
        assert "#active" not in replacement
        assert "#keep" in replacement
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "new_hash": "sha256:hash1",
                "new_line_count": 7,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_tags(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "remove",
                "tags": ["active"],
            },
        )
    )

    assert result["removed"] == ["active"]
    assert "active" not in str(result["tags"])
    assert "keep" in str(result["tags"])
    assert len(calls) == _EXPECTED_PATCH_CALLS


def test_manage_tags_list_returns_union_of_frontmatter_and_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = "---\ntags:\n  - project\n---\n\nBody #active #project"

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        assert method == "GET"
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "content": note_content,
                "content_hash": "sha256:hash0",
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_tags(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "list",
            },
        )
    )

    assert result["tags"] == ["project", "active"]
    assert len(calls) == 1


def test_manage_frontmatter_preserves_other_frontmatter_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_session()
    calls: list[tuple[str, dict[str, object], str]] = []
    note_content = (
        "---\n"
        "title: Note\n"
        "# keep this comment\n"
        "status: active\n"
        "aliases:\n"
        "  - one\n"
        "  - two\n"
        "---\n"
        "\n"
        "Body"
    )

    def response_for_url(
        url: str, payload: dict[str, object], method: str
    ) -> FakeResponse:
        if method == "GET":
            return FakeResponse(
                200,
                {
                    "path": "Notes/Test.md",
                    "content": note_content,
                    "content_hash": "sha256:hash0",
                },
            )
        assert method == "PATCH"
        replacement = str(payload["replacement"])
        assert "title: Note" in replacement
        assert "# keep this comment" in replacement
        assert "aliases:" in replacement
        assert "  - one" in replacement
        assert "status: archived" in replacement
        return FakeResponse(
            200,
            {
                "path": "Notes/Test.md",
                "new_hash": "sha256:hash1",
                "new_line_count": 10,
            },
        )

    install_fake_client(monkeypatch, response_for_url, calls)
    settings = Settings(vector_search_url="http://vector.local")

    result = asyncio.run(
        mcp_search.do_manage_frontmatter(
            settings,
            {
                "path": "Notes/Test.md",
                "operation": "set",
                "key": "status",
                "value": "archived",
            },
        )
    )

    assert result["value"] == "archived"
    assert len(calls) == _EXPECTED_PATCH_CALLS
