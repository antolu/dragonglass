from __future__ import annotations

import datetime
import json
import logging
import time
import typing

import fastmcp
import httpx
import pydantic
from pydantic import JsonValue

from dragonglass.config import Settings
from dragonglass.hybrid_search import SearchEngine
from dragonglass.mcp.edit.frontmatter import ManageFrontmatterArgs, ManageTagsArgs
from dragonglass.mcp.edit.notes import (
    do_manage_frontmatter,
    do_patch_note_lines,
    do_read_note_with_hash,
)
from dragonglass.mcp.edit.tags import do_manage_tags
from dragonglass.mcp.telemetry import ToolPhase, emit_tool_event

logger = logging.getLogger(__name__)


def _coerce_json_string_to_list(v: JsonValue) -> JsonValue:
    if isinstance(v, str):
        try:
            return typing.cast(JsonValue, json.loads(v))
        except (json.JSONDecodeError, TypeError):
            return [v]
    return v


_StringList = typing.Annotated[
    list[str], pydantic.BeforeValidator(_coerce_json_string_to_list)
]


def create_search_server(engine: SearchEngine, settings: Settings) -> fastmcp.FastMCP:  # noqa: PLR0915
    m = fastmcp.FastMCP("search")

    def _safe_value_preview(value: JsonValue, limit: int = 160) -> str:
        text = str(value)
        if len(text) <= limit:
            return text
        return text[:limit] + f"... [truncated {len(text) - limit} chars]"

    @m.tool(name="dragonglass_new_search_session")
    def new_search_session() -> dict[str, str]:
        """Create a new search session. Destroys any previous session.
        MUST be called before starting keyword or vector searches.
        """
        session = engine.new_session()
        emit_tool_event(
            "dragonglass_new_search_session",
            ToolPhase.DONE,
            "New search session",
            f"id={session.id}",
        )
        return {"session_id": session.id, "status": "created"}

    @m.tool(name="dragonglass_get_date_context")
    def get_date_context(
        offset_days: int = 0,
    ) -> dict[str, str | list[dict[str, str]]]:
        """Return the date, day of week, and week calendar anchored at today + offset_days.

        Call this when the user refers to dates relatively (e.g. "next Sunday",
        "last week", "yesterday") so you can resolve the correct ISO date before
        searching the vault. Use offset_days to shift the anchor: -7 for last week,
        +7 for next week, -14 for two weeks ago, etc.
        """
        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        today = datetime.date.today()
        anchor = today + datetime.timedelta(days=offset_days)
        monday = anchor - datetime.timedelta(days=anchor.weekday())
        week = [
            {
                "day": day_names[i],
                "date": (monday + datetime.timedelta(days=i)).isoformat(),
            }
            for i in range(7)
        ]
        return {
            "today": today.isoformat(),
            "anchor": anchor.isoformat(),
            "day_of_week": day_names[anchor.weekday()],
            "week": week,
        }

    @m.tool(name="dragonglass_keyword_search")
    async def keyword_search(
        queries: _StringList | None = None,
        query: str | None = None,
    ) -> dict[str, JsonValue]:
        """Search the vault for files matching one or more text queries.

        Args:
            queries: A list of search strings, e.g., ["meeting notes", "project alpha"].
            query: Alias for queries; accepts a single search string.

        At least one of `queries` or `query` must be provided. Pass multiple
        complementary strings in `queries` to improve search coverage.
        """
        if query and not queries:
            queries = [query]
        if not queries:
            return {"error": "At least one search query is required"}

        started = time.monotonic()
        try:
            await engine.keyword_search(queries)
        except RuntimeError as exc:
            return {"error": str(exc)}
        elapsed = time.monotonic() - started

        session = engine.session
        all_paths = session.allowlist if session else []
        terms = ", ".join(str(q) for q in queries)
        emit_tool_event(
            "dragonglass_keyword_search",
            ToolPhase.DONE,
            f"Keyword search: {terms}",
            f"{len(all_paths)} files found ({elapsed:.2f}s)",
        )
        return {
            "total_found": len(all_paths),
            "query_count": len(queries),
            "preview_paths": typing.cast(list[JsonValue], all_paths[:10]),
        }

    @m.tool(name="dragonglass_vector_search")
    async def vector_search(
        query: str, top_n: int = 10, min_score: float = 0.35
    ) -> list[dict[str, JsonValue]]:
        """Perform semantic (vector) search to find notes by meaning.

        Args:
            query: a natural language description of what you are looking for.
            top_n: maximum number of results to return (default: 10).
            min_score: minimum similarity score [0..1] (default: 0.35).
        """
        started = time.monotonic()
        try:
            hits = await engine.vector_search(query, top_n=top_n, min_score=min_score)
        except RuntimeError as exc:
            return [{"error": str(exc)}]
        elapsed = time.monotonic() - started
        result: list[dict[str, JsonValue]] = [
            {"path": h.path, "score": h.score} for h in hits
        ]
        emit_tool_event(
            "dragonglass_vector_search",
            ToolPhase.DONE,
            f"Vector search: {_safe_value_preview(query, 80)}",
            f"{len(result)} hits ({elapsed:.2f}s)",
        )
        return result

    @m.tool(name="dragonglass_run_command")
    async def run_command(command_id: str) -> dict[str, str]:
        """Execute an Obsidian command by its ID."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{settings.vector_search_url}/commands/{command_id}",
                )
                if resp.status_code in {httpx.codes.OK, httpx.codes.NO_CONTENT}:
                    emit_tool_event(
                        "dragonglass_run_command",
                        ToolPhase.DONE,
                        f"Run command: {_safe_value_preview(command_id)}",
                        "ok",
                    )
                    return {"status": "executed", "command_id": command_id}
                emit_tool_event(
                    "dragonglass_run_command",
                    ToolPhase.ERROR,
                    f"Run command: {_safe_value_preview(command_id)}",
                    f"HTTP {resp.status_code}",
                )
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("run_command failed for %r", command_id)
            emit_tool_event(
                "dragonglass_run_command",
                ToolPhase.ERROR,
                f"Run command: {_safe_value_preview(command_id)}",
                _safe_value_preview(str(exc)),
            )
            return {"error": str(exc)}

    @m.tool(name="dragonglass_read_note_with_hash")
    async def read_note_with_hash(
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> dict[str, JsonValue]:
        """Read a markdown note and store its content hash in session state.

        Returns content with line numbers (L1: ..., L2: ...) to make it easy to
        identify ranges for `patch_note_lines`. Use `start_line` and `end_line`
        to request only a portion of the note; the full content hash will still
        be captured for atomic patching.

        Must be called before patch_note_lines unless expected_hash is provided.
        """
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
        started = time.monotonic()
        result = await do_read_note_with_hash(
            settings, path, session, start_line, end_line
        )
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"{result.get('total_lines', '?')} lines ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_read_note_with_hash",
            phase,
            f"Reading: {_safe_value_preview(path, 80)}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_replace_lines")
    async def replace_lines(
        path: str,
        start_line: int,
        end_line: int,
        replacement: str,
        expected_hash: str | None = None,
    ) -> dict[str, JsonValue]:
        """Replace a 1-based inclusive line range in a note with new text.

        Use this when you need to modify existing content (e.g. rewrite a sentence
        or paragraph). Do NOT use this to insert — use dragonglass_insert_after_line
        instead, as using replace for insertion will overwrite existing lines.

        If expected_hash is omitted, uses the hash from the current session
        (captured by read_note_with_hash). The hash covers the entire file.
        """
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
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
            session,
        )
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_replace_lines",
            phase,
            f"Replacing: {_safe_value_preview(path, 60)} lines {start_line}-{end_line}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_insert_after_line")
    async def insert_after_line(
        path: str,
        line: int,
        text: str,
        expected_hash: str | None = None,
    ) -> dict[str, JsonValue]:
        """Insert new text after a given 1-based line number without overwriting anything.

        Use this to add new content (new sentences, list items, paragraphs) after
        an existing line. To append to the end of the file, pass the last line number.

        If expected_hash is omitted, uses the hash from the current session
        (captured by read_note_with_hash).
        """
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
        started = time.monotonic()
        result = await do_patch_note_lines(
            settings,
            {
                "path": path,
                "start_line": line + 1,
                "end_line": line,
                "replacement": text,
                "expected_hash": expected_hash,
            },
            session,
        )
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_insert_after_line",
            phase,
            f"Inserting: {_safe_value_preview(path, 60)} after line {line}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_delete_lines")
    async def delete_lines(
        path: str,
        start_line: int,
        end_line: int,
        expected_hash: str | None = None,
    ) -> dict[str, JsonValue]:
        """Delete a 1-based inclusive line range from a note.

        Use this to remove lines entirely. To replace content, use
        dragonglass_replace_lines instead.

        If expected_hash is omitted, uses the hash from the current session
        (captured by read_note_with_hash).
        """
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
        started = time.monotonic()
        result = await do_patch_note_lines(
            settings,
            {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "replacement": "",
                "expected_hash": expected_hash,
            },
            session,
        )
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_delete_lines",
            phase,
            f"Deleting: {_safe_value_preview(path, 60)} lines {start_line}-{end_line}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_manage_frontmatter")
    async def manage_frontmatter(
        path: str,
        operation: typing.Literal["get", "set", "delete"],
        key: str,
        value: JsonValue = None,
    ) -> dict[str, JsonValue]:
        """Get, set, or delete a frontmatter key."""
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
        started = time.monotonic()
        args: ManageFrontmatterArgs = {
            "path": path,
            "operation": operation,
            "key": key,
        }
        if operation == "set":
            args["value"] = value
        result = await do_manage_frontmatter(settings, args, session)
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_manage_frontmatter",
            phase,
            f"Frontmatter: {operation} {_safe_value_preview(key)} in {_safe_value_preview(path, 60)}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_manage_tags")
    async def manage_tags(
        path: str,
        operation: typing.Literal["add", "remove", "list"],
        tags: list[str] | None = None,
    ) -> dict[str, JsonValue]:
        """Add, remove, or list note tags."""
        session = engine.session
        if session is None:
            return {
                "error": "No active search session. Call dragonglass_new_search_session first."
            }
        started = time.monotonic()
        args: ManageTagsArgs = {
            "path": path,
            "operation": operation,
        }
        if tags is not None:
            args["tags"] = tags
        result = await do_manage_tags(settings, args, session)
        elapsed = time.monotonic() - started
        phase = ToolPhase.ERROR if "error" in result else ToolPhase.DONE
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_manage_tags",
            phase,
            f"Tags: {operation} in {_safe_value_preview(path, 60)}",
            detail,
        )
        return result

    return m
