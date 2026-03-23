from __future__ import annotations

import json
import logging
import time
import typing
import urllib.parse

import fastmcp
import httpx
import pydantic

from dragonglass.config import Settings
from dragonglass.mcp.telemetry import emit_tool_event
from dragonglass.search.session import get_current_session, new_session

logger = logging.getLogger(__name__)


def _coerce_json_string_to_list(v: typing.Any) -> typing.Any:
    if isinstance(v, str):
        return json.loads(v)
    return v


_StringList = typing.Annotated[
    list[str], pydantic.BeforeValidator(_coerce_json_string_to_list)
]


class PatchLinesArgs(typing.TypedDict):
    path: str
    start_line: int
    end_line: int
    replacement: str
    expected_hash: str | None


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
) -> dict[str, typing.Any]:
    session = get_current_session()
    if not session:
        return {"error": "No active search session. Call new_search_session first."}

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


_NOTE_ERROR_MESSAGES: dict[str, str] = {
    "note_not_found": "Note not found in vault. The file may have been deleted or the path is wrong.",
    "invalid_path": "Path must end with .md.",
    "invalid_body": "Malformed request body.",
}

_PATCH_ERROR_MESSAGES: dict[str, str] = {
    "note_not_found": "Note not found in vault. The file may have been deleted or the path is wrong.",
    "hash_mismatch": "Note was modified since it was last read. Call read_note_with_hash again before patching.",
    "line_range_out_of_bounds": "Line range exceeds the number of lines in the note.",
    "invalid_line_range": "Invalid line range: start_line must be >= 1 and <= end_line.",
}


def _parse_response_json(resp: httpx.Response) -> dict[str, typing.Any] | None:
    try:
        result = resp.json()
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return None


async def do_read_note_with_hash(  # noqa: PLR0911
    settings: Settings,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> dict[str, typing.Any]:
    session = get_current_session()
    if not session:
        return {"error": "No active search session. Call new_search_session first."}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.vector_search_url}/notes/read",
                params={"path": path},
            )
            if resp.status_code == httpx.codes.OK:
                data = _parse_response_json(resp)
                if data is None:
                    return {"error": "Vector search server returned empty response."}
                content_hash = data.get("content_hash")
                if isinstance(content_hash, str):
                    session.set_last_read_hash(path, content_hash)

                content = data.get("content", "")
                lines = content.splitlines()
                total_lines = len(lines)

                # Format content with line numbers
                # We use L{n}: format to be clear for the LLM
                formatted_lines = [f"L{i + 1}: {line}" for i, line in enumerate(lines)]

                if start_line is not None or end_line is not None:
                    s = (start_line if start_line is not None else 1) - 1
                    e = end_line if end_line is not None else total_lines
                    # Clamp values
                    s = max(0, min(s, total_lines))
                    e = max(s, min(e, total_lines))
                    display_lines = formatted_lines[s:e]
                else:
                    display_lines = formatted_lines

                data["content_with_line_numbers"] = "\n".join(display_lines)
                data["total_lines"] = total_lines
                return data

            data = _parse_response_json(resp)
            error_code = data.get("error", "") if data else ""
            message = _NOTE_ERROR_MESSAGES.get(error_code)
            if message:
                return {"error": message}
            if data:
                return {"error": f"HTTP {resp.status_code}", "details": data}
            return {
                "error": (
                    f"Vector search server returned HTTP {resp.status_code} with no body. "
                    "The Obsidian plugin may not be running or may need to be reloaded."
                )
            }
    except httpx.ConnectError:
        return {
            "error": (
                f"Cannot connect to vector search server at {settings.vector_search_url}. "
                "The Obsidian plugin is likely not running."
            )
        }
    except Exception as exc:
        logger.exception("read_note_with_hash failed for path %r", path)
        return {"error": str(exc)}


async def do_patch_note_lines(  # noqa: PLR0911
    settings: Settings,
    args: PatchLinesArgs,
) -> dict[str, typing.Any]:
    session = get_current_session()
    if not session:
        return {"error": "No active search session. Call new_search_session first."}

    path = args["path"]
    resolved_expected_hash = args["expected_hash"] or session.get_last_read_hash(path)
    if not resolved_expected_hash:
        return {
            "error": (
                "No stored hash for this file. Call read_note_with_hash(path) before "
                "patch_note_lines(path, ...)."
            )
        }

    payload = {
        "path": path,
        "start_line": args["start_line"],
        "end_line": args["end_line"],
        "replacement": args["replacement"],
        "expected_hash": resolved_expected_hash,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{settings.vector_search_url}/notes/patch-lines",
                json=payload,
            )
            if resp.status_code == httpx.codes.OK:
                data = _parse_response_json(resp)
                if data is None:
                    return {"error": "Vector search server returned empty response."}
                new_hash = data.get("new_hash")
                if isinstance(new_hash, str):
                    session.set_last_read_hash(path, new_hash)
                return data

            data = _parse_response_json(resp)
            error_code = data.get("error", "") if data else ""
            message = _PATCH_ERROR_MESSAGES.get(error_code)
            if message:
                return {"error": message}
            if data:
                return {"error": f"HTTP {resp.status_code}", "details": data}
            return {
                "error": (
                    f"Vector search server returned HTTP {resp.status_code} with no body. "
                    "The Obsidian plugin may not be running or may need to be reloaded."
                )
            }
    except httpx.ConnectError:
        return {
            "error": (
                f"Cannot connect to vector search server at {settings.vector_search_url}. "
                "The Obsidian plugin is likely not running."
            )
        }
    except Exception as exc:
        logger.exception("patch_note_lines failed for path %r", path)
        return {"error": str(exc)}


def create_search_server(settings: Settings) -> fastmcp.FastMCP:  # noqa: PLR0915
    m = fastmcp.FastMCP("search")

    def _safe_value_preview(value: object, limit: int = 160) -> str:
        text = str(value)
        if len(text) <= limit:
            return text
        return text[:limit] + f"... [truncated {len(text) - limit} chars]"

    @m.tool(name="dragonglass_new_search_session")
    def new_search_session() -> dict[str, str]:
        """Create a new search session. Destroys any previous session.
        MUST be called before starting keyword or vector searches.
        """
        emit_tool_event(
            "dragonglass_new_search_session",
            "start",
            "Creating new search session",
        )
        session = new_session()
        emit_tool_event(
            "dragonglass_new_search_session",
            "done",
            f"Search session created id={session.id}",
        )
        return {"session_id": session.id, "status": "created"}

    @m.tool(name="dragonglass_keyword_search")
    async def keyword_search(queries: _StringList) -> dict[str, typing.Any]:
        """Search the vault for files matching one or more text queries."""
        emit_tool_event(
            "dragonglass_keyword_search",
            "start",
            f"Running keyword search for {len(queries)} queries",
        )
        started = time.monotonic()
        result = await _do_keyword_search(settings, queries)
        elapsed = time.monotonic() - started
        if "error" in result:
            emit_tool_event(
                "dragonglass_keyword_search",
                "error",
                _safe_value_preview(result.get("error")),
            )
        else:
            emit_tool_event(
                "dragonglass_keyword_search",
                "done",
                (
                    f"Keyword search complete in {elapsed:.2f}s "
                    f"(total_found={result.get('total_found', 0)})"
                ),
            )
        return result

    @m.tool(name="dragonglass_vector_search")
    async def vector_search(
        query: str, top_n: int = 10, min_score: float = 0.35
    ) -> list[dict[str, typing.Any]]:
        """Perform semantic (vector) search."""
        emit_tool_event(
            "dragonglass_vector_search",
            "start",
            f"Running vector search top_n={top_n} min_score={min_score}",
        )
        started = time.monotonic()
        result = await _do_vector_search(settings, query, top_n, min_score)
        elapsed = time.monotonic() - started
        errors = [item.get("error") for item in result if isinstance(item, dict)]
        errors = [err for err in errors if isinstance(err, str)]
        if errors:
            emit_tool_event(
                "dragonglass_vector_search",
                "error",
                _safe_value_preview(errors[0]),
            )
        else:
            emit_tool_event(
                "dragonglass_vector_search",
                "done",
                f"Vector search complete in {elapsed:.2f}s (hits={len(result)})",
            )
        return result

    @m.tool(name="dragonglass_open_note")
    async def open_note(path: str) -> dict[str, str]:
        """Open a note in Obsidian by its vault-relative path."""
        emit_tool_event(
            "dragonglass_open_note",
            "start",
            f"Opening note {_safe_value_preview(path)}",
        )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                encoded = urllib.parse.quote(path, safe="/")
                resp = await client.post(
                    f"{settings.vector_search_url}/open/{encoded}",
                )
                if resp.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
                    emit_tool_event(
                        "dragonglass_open_note",
                        "done",
                        f"Opened note {_safe_value_preview(path)}",
                    )
                    return {"status": "opened", "path": path}
                emit_tool_event(
                    "dragonglass_open_note",
                    "error",
                    f"HTTP {resp.status_code}",
                )
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("open_note failed for path %r", path)
            emit_tool_event(
                "dragonglass_open_note",
                "error",
                _safe_value_preview(exc),
            )
            return {"error": str(exc)}

    @m.tool(name="dragonglass_run_command")
    async def run_command(command_id: str) -> dict[str, str]:
        """Execute an Obsidian command by its ID."""
        emit_tool_event(
            "dragonglass_run_command",
            "start",
            f"Running command {_safe_value_preview(command_id)}",
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.vector_search_url}/commands/{command_id}",
                )
                if resp.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
                    emit_tool_event(
                        "dragonglass_run_command",
                        "done",
                        f"Executed command {_safe_value_preview(command_id)}",
                    )
                    return {"status": "executed", "command_id": command_id}
                emit_tool_event(
                    "dragonglass_run_command",
                    "error",
                    f"HTTP {resp.status_code}",
                )
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("run_command failed for %r", command_id)
            emit_tool_event(
                "dragonglass_run_command",
                "error",
                _safe_value_preview(exc),
            )
            return {"error": str(exc)}

    @m.tool(name="dragonglass_read_note_with_hash")
    async def read_note_with_hash(
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> dict[str, typing.Any]:
        """Read a markdown note and store its content hash in session state.

        Returns content with line numbers (L1: ..., L2: ...) to make it easy to
        identify ranges for `patch_note_lines`. Use `start_line` and `end_line`
        to request only a portion of the note; the full content hash will still
        be captured for atomic patching.

        Must be called before patch_note_lines unless expected_hash is provided.
        """
        emit_tool_event(
            "dragonglass_read_note_with_hash",
            "start",
            f"Reading note {_safe_value_preview(path)}",
        )
        started = time.monotonic()
        result = await do_read_note_with_hash(settings, path, start_line, end_line)
        elapsed = time.monotonic() - started
        if "error" in result:
            emit_tool_event(
                "dragonglass_read_note_with_hash",
                "error",
                _safe_value_preview(result.get("error")),
            )
        else:
            emit_tool_event(
                "dragonglass_read_note_with_hash",
                "done",
                f"Read note complete in {elapsed:.2f}s",
            )
        return result

    @m.tool(name="dragonglass_patch_note_lines")
    async def patch_note_lines(
        path: str,
        start_line: int,
        end_line: int,
        replacement: str,
        expected_hash: str | None = None,
    ) -> dict[str, typing.Any]:
        """Replace a 1-based inclusive line range in a markdown note.

        If expected_hash is omitted, the tool uses the hash captured by
        read_note_with_hash(path) from the current search session.
        Note that read_note_with_hash captures the hash of the ENTIRE file,
        which is required for this tool to ensure atomicity even if only
        a subset of lines was read.
        """
        emit_tool_event(
            "dragonglass_patch_note_lines",
            "start",
            (
                f"Patching note {_safe_value_preview(path)} lines "
                f"{start_line}-{end_line}"
            ),
        )
        started = time.monotonic()
        result = await do_patch_note_lines(
            settings,
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "replacement": replacement,
                "expected_hash": expected_hash,
            },
        )
        elapsed = time.monotonic() - started
        if "error" in result:
            emit_tool_event(
                "dragonglass_patch_note_lines",
                "error",
                _safe_value_preview(result.get("error")),
            )
        else:
            emit_tool_event(
                "dragonglass_patch_note_lines",
                "done",
                f"Patch complete in {elapsed:.2f}s",
            )
        return result

    return m
