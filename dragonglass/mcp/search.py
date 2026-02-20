from __future__ import annotations

import logging
import typing
import urllib.parse

import fastmcp
import httpx

from dragonglass.config import Settings
from dragonglass.search.session import get_current_session, new_session

logger = logging.getLogger(__name__)


async def _keyword_search_task(
    client: httpx.AsyncClient,
    query: str,
    obsidian_url: str,
    headers: dict[str, str],
) -> list[str]:
    try:
        resp = await client.post(
            f"{obsidian_url}/search/simple/",
            params={"query": query, "contextLength": 0},
            headers=headers,
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
) -> dict[str, typing.Any]:
    session = get_current_session()
    if not session:
        return {"error": "No active search session. Call new_search_session first."}

    found_paths: set[str] = set()
    logger.debug("keyword_search  queries=%s", queries)

    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        headers = {"Authorization": f"Bearer {settings.obsidian_api_key}"}
        for query in queries:
            paths = await _keyword_search_task(
                client, query, settings.obsidian_api_url, headers
            )
            found_paths.update(paths)

    session.add_keyword_results(list(found_paths))
    all_paths = sorted(session.file_paths)
    logger.debug("keyword_search  session_paths=%s", all_paths)
    return {
        "total_found": len(all_paths),
        "query_count": len(queries),
        "preview_paths": all_paths[:10],
    }


async def _do_vector_search(
    settings: Settings, query: str, top_n: int, min_score: float
) -> list[dict[str, typing.Any]]:
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
            payload: dict[str, typing.Any] = {
                "text": query,
                "top_n": top_n,
                "min_score": effective_min,
            }
            if allowlist:
                payload["allowlist"] = allowlist

            resp = await client.post(
                f"{settings.vector_search_url}/search/text",
                json=payload,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            filtered = [r for r in results if r.get("score", 0) >= effective_min]
            logger.debug(
                "vector_search  returned=%d  after_filter=%d  results=%s",
                len(results),
                len(filtered),
                [(r.get("path", "?"), round(r.get("score", 0), 3)) for r in filtered],
            )
            return filtered
    except Exception as e:
        logger.exception("vector search failed")
        return [{"error": f"Vector search error: {e}"}]


def create_search_server(settings: Settings) -> fastmcp.FastMCP:
    m = fastmcp.FastMCP("search")

    @m.tool()
    def new_search_session() -> dict[str, str]:
        """Create a new search session. Destroys any previous session.
        MUST be called before starting keyword or vector searches.
        """
        session = new_session()
        return {"session_id": session.id, "status": "created"}

    @m.tool()
    async def keyword_search(queries: list[str]) -> dict[str, typing.Any]:
        """Perform keyword search in the vault using multiple query strings.
        Queries can use prefixes like file:, tag:, section:, property:.
        Results across ALL queries are merged into the current session's allowlist.
        Returns the total number of unique files found and a preview of the first paths.
        """
        return await _do_keyword_search(settings, queries)

    @m.tool()
    async def vector_search(
        query: str, top_n: int = 10, min_score: float = 0.35
    ) -> list[dict[str, typing.Any]]:
        """Perform semantic (vector) search.
        If keyword_search was called previously in this session, this search is restricted
        to those files (allowlist). If no keywords were found, it falls back to a global search.

        A min_score of 0.35-0.40 is generally good for filtering noise.
        """
        return await _do_vector_search(settings, query, top_n, min_score)

    @m.tool()
    async def open_note(path: str) -> dict[str, str]:
        """Open a note in Obsidian by its vault-relative path."""
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                encoded = urllib.parse.quote(path, safe="/")
                resp = await client.post(
                    f"{settings.obsidian_api_url}/open/{encoded}",
                    headers={"Authorization": f"Bearer {settings.obsidian_api_key}"},
                )
                if resp.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
                    return {"status": "opened", "path": path}
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("open_note failed for path %r", path)
            return {"error": str(exc)}

    @m.tool()
    async def run_command(command_id: str) -> dict[str, str]:
        """Execute an Obsidian command by its ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.post(
                    f"{settings.obsidian_api_url}/commands/{command_id}",
                    headers={"Authorization": f"Bearer {settings.obsidian_api_key}"},
                )
                if resp.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
                    return {"status": "executed", "command_id": command_id}
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("run_command failed for %r", command_id)
            return {"error": str(exc)}

    return m
