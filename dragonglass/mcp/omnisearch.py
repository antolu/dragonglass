from __future__ import annotations

import fastmcp
import httpx

from dragonglass.config import Settings


def create_omnisearch_server(settings: Settings) -> fastmcp.FastMCP:
    mcp = fastmcp.FastMCP("omnisearch")

    @mcp.tool()
    async def search_vault(query: str, limit: int = 10) -> list[dict[str, str | float]]:
        """Search the Obsidian vault using Omnisearch for fuzzy full-text search.

        Returns a list of matching notes with their path, score, and a content excerpt.
        If Omnisearch is unavailable (Obsidian closed), returns an error dict.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.omnisearch_url}/search",
                    params={"q": query},
                )
                resp.raise_for_status()
                results = resp.json()
                return [
                    {
                        "path": r.get("path", r.get("basename", "")),
                        "score": r.get("score", 0.0),
                        "excerpt": r.get("excerpt", ""),
                    }
                    for r in results[:limit]
                ]
        except httpx.ConnectError:
            return [
                {
                    "error": (
                        "Omnisearch is not available. Make sure Obsidian is open "
                        "and the Omnisearch HTTP server is enabled in its settings. "
                        "Falling back to MCP global search is recommended."
                    )
                }
            ]
        except Exception as exc:
            return [{"error": f"Omnisearch error: {exc}"}]

    return mcp
