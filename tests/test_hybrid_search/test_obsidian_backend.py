from __future__ import annotations

import asyncio
import types
from typing import Self

import httpx
import pytest

from dragonglass.search.backends import ObsidianHttpBackend


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: list[dict[str, object]] | dict[str, object],
    ) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> list[dict[str, object]] | dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:  # noqa: PLR2004
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=None,  # type: ignore[arg-type]
                response=None,  # type: ignore[arg-type]
            )


class FakeAsyncClient:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, object]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        pass

    async def post(
        self,
        url: str,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
    ) -> FakeResponse:
        self.calls.append((url, params or json))
        return self._response


def test_keyword_search_returns_keyword_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeAsyncClient(
        FakeResponse(200, [{"filename": "note1.md"}, {"filename": "note2.md"}])
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    hits = asyncio.run(backend.keyword_search(["foo"]))

    assert len(hits) == 2  # noqa: PLR2004
    assert hits[0].path == "note1.md"
    assert hits[1].path == "note2.md"


def test_keyword_search_deduplicates_across_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeAsyncClient(FakeResponse(200, [{"filename": "note1.md"}]))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    hits = asyncio.run(backend.keyword_search(["foo", "bar"]))

    assert len(hits) == 1
    assert hits[0].path == "note1.md"


def test_keyword_search_handles_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeAsyncClient(FakeResponse(500, {}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    hits = asyncio.run(backend.keyword_search(["foo"]))
    assert hits == []


def test_vector_search_returns_vector_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeAsyncClient(
        FakeResponse(
            200,
            {
                "results": [
                    {"path": "a.md", "score": 0.8},
                    {"path": "b.md", "score": 0.6},
                ]
            },
        )
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    hits = asyncio.run(backend.vector_search("semantic query", min_score=0.35))

    assert len(hits) == 2  # noqa: PLR2004
    assert hits[0].path == "a.md"
    assert hits[0].score == pytest.approx(0.8)


def test_vector_search_filters_by_min_score(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeAsyncClient(
        FakeResponse(
            200,
            {
                "results": [
                    {"path": "a.md", "score": 0.8},
                    {"path": "b.md", "score": 0.2},
                ]
            },
        )
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    hits = asyncio.run(backend.vector_search("query", min_score=0.5))

    assert len(hits) == 1
    assert hits[0].path == "a.md"


def test_vector_search_passes_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = FakeAsyncClient(FakeResponse(200, {"results": []}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: fake_client)

    backend = ObsidianHttpBackend(base_url="http://localhost:51362")
    asyncio.run(backend.vector_search("query", allowlist=["a.md", "b.md"]))

    _, payload = fake_client.calls[0]
    assert isinstance(payload, dict)
    assert payload["allowlist"] == ["a.md", "b.md"]
