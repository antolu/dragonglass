from __future__ import annotations

import urllib.parse
from typing import Any

import fastmcp
import httpx

from dragonglass.config import Settings
from dragonglass.search.session import get_current_session, new_session


async def _keyword_search_task(
    client: httpx.AsyncClient,
    query: str,
    obsidian_url: str,
    headers: dict[str, str],
) -> list[str]:
    try:
        resp = await client.get(
            f"{obsidian_url}/search/",
            params={"query": query},
            headers=headers,
        )
        if resp.status_code == httpx.codes.OK:
            results = resp.json()
            return [
                r.get("path", r.get("filename", ""))
                for r in results
                if r.get("path") or r.get("filename")
            ]
    except Exception as e:
        # We don't want to crash the whole search if one query fails
        print(f"Error during keyword search for '{query}': {e}")
    return []


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
    async def keyword_search(queries: list[str]) -> dict[str, Any]:
        """Perform keyword search in the vault using multiple query strings.
        Queries can use prefixes like file:, tag:, section:, property:.
        Results across ALL queries are merged into the current session's allowlist.
        Returns the total number of unique files found.
        """
        session = get_current_session()
        if not session:
            return {"error": "No active search session. Call new_search_session first."}

        found_paths: set[str] = set()

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            headers = {"Authorization": f"Bearer {settings.obsidian_api_key}"}
            for query in queries:
                paths = await _keyword_search_task(
                    client, query, settings.obsidian_api_url, headers
                )
                found_paths.update(paths)

        session.add_keyword_results(list(found_paths))
        return {"total_found": len(session.file_paths), "query_count": len(queries)}

    @m.tool()
    async def vector_search(query: str, top_n: int = 10) -> list[dict[str, Any]]:
        """Perform semantic (vector) search.
        If keyword_search was called previously in this session, this search is restricted
        to those files (allowlist). If no keywords were found, it falls back to a global search.
        """
        session = get_current_session()
        allowlist = session.allowlist if session else []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {"text": query, "top_n": top_n}
                if allowlist:
                    payload["allowlist"] = allowlist

                resp = await client.post(
                    f"{settings.vector_search_url}/search/text",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except Exception as e:
            return [{"error": f"Vector search error: {e}"}]

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
            return {"error": str(exc)}

    return m
