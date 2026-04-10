from __future__ import annotations

import json
import logging
import typing

import httpx
import pydantic
from pydantic import JsonValue

from dragonglass.config import Settings
from dragonglass.search.session import get_current_session

logger = logging.getLogger(__name__)


def _coerce_json_string_to_list(v: JsonValue) -> JsonValue:
    if isinstance(v, str):
        try:
            return typing.cast(JsonValue, json.loads(v))
        except (json.JSONDecodeError, TypeError):
            return [v]
    return v


def _coerce_json_map(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    return {key: item for key, item in value.items() if isinstance(key, str)}


_StringList = typing.Annotated[
    list[str], pydantic.BeforeValidator(_coerce_json_string_to_list)
]


async def _keyword_search_task(
    client: httpx.AsyncClient,
    query: str,
    vector_search_url: str,
) -> list[str]:
    try:
        resp = await client.post(
            f"{vector_search_url}/search/simple/",
            params={"query": query, "contextLength": 0},
        )
        logger.debug(
            "_keyword_search_task  query=%r  status=%d  raw_hits=%d  paths=%s",
            query,
            resp.status_code,
            len(resp.json()) if resp.status_code == httpx.codes.OK else 0,
            [r.get("filename", "") for r in resp.json()]
            if resp.status_code == httpx.codes.OK
            else resp.text[:300],
        )
        if resp.status_code == httpx.codes.OK:
            results = resp.json()
            return [r["filename"] for r in results if r.get("filename")]
    except Exception:
        logger.exception("keyword search failed for query %r", query)
    return []


async def _do_keyword_search(
    settings: Settings, queries: list[str]
) -> dict[str, JsonValue]:
    session = get_current_session()
    if not session:
        return {
            "error": "No active search session. Call dragonglass_new_search_session first."
        }

    found_paths: set[str] = set()
    logger.debug("keyword_search  queries=%s", queries)

    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        for query in queries:
            paths = await _keyword_search_task(
                client, query, settings.vector_search_url
            )
            found_paths.update(paths)

    session.add_keyword_results(list(found_paths))
    all_paths = sorted(session.file_paths)
    logger.debug("keyword_search  session_paths=%s", all_paths)
    return {
        "total_found": len(all_paths),
        "query_count": len(queries),
        "preview_paths": typing.cast(list[JsonValue], all_paths[:10]),
    }


async def _do_vector_search(
    settings: Settings, query: str, top_n: int, min_score: float
) -> list[dict[str, JsonValue]]:
    session = get_current_session()
    allowlist = session.allowlist if session else []
    effective_min = 0.5 if allowlist else min_score

    logger.debug(
        "vector_search  query=%r  top_n=%d  min_score=%.2f  allowlist=%d files",
        query,
        top_n,
        effective_min,
        len(allowlist),
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload: dict[str, JsonValue] = {
                "text": query,
                "top_n": top_n,
                "min_score": effective_min,
            }
            if allowlist:
                payload["allowlist"] = typing.cast(list[JsonValue], allowlist)

            resp = await client.post(
                f"{settings.vector_search_url}/search/text",
                json=payload,
            )
            resp.raise_for_status()
            body = _coerce_json_map(typing.cast(JsonValue, resp.json()))
            raw_results = body.get("results")
            results = raw_results if isinstance(raw_results, list) else []
            typed_results = [
                _coerce_json_map(typing.cast(JsonValue, item)) for item in results
            ]
            filtered: list[dict[str, JsonValue]] = []
            for row in typed_results:
                score_raw = row.get("score")
                if (
                    isinstance(score_raw, int | float)
                    and float(score_raw) >= effective_min
                ):
                    filtered.append(row)
            preview_scores: list[tuple[JsonValue, float]] = []
            for row in filtered:
                score_raw = row.get("score", 0.0)
                score = float(score_raw) if isinstance(score_raw, int | float) else 0.0
                preview_scores.append((row.get("path", "?"), round(score, 3)))
            logger.debug(
                "vector_search  returned=%d  after_filter=%d  results=%s",
                len(typed_results),
                len(filtered),
                preview_scores,
            )
            return filtered
    except Exception as e:
        logger.exception("vector search failed")
        return [{"error": f"Vector search error: {e}"}]
