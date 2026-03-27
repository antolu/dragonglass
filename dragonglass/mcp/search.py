from __future__ import annotations

import json
import logging
import re
import time
import typing

import fastmcp
import httpx
import pydantic

from dragonglass.config import Settings
from dragonglass.mcp.telemetry import emit_tool_event
from dragonglass.search.session import get_current_session, new_session

logger = logging.getLogger(__name__)


def _coerce_json_string_to_list(v: typing.Any) -> typing.Any:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [v]
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


class ManageFrontmatterArgs(typing.TypedDict):
    path: str
    operation: typing.Literal["get", "set", "delete"]
    key: str
    value: typing.NotRequired[typing.Any]


class ManageTagsArgs(typing.TypedDict):
    path: str
    operation: typing.Literal["add", "remove", "list"]
    tags: typing.NotRequired[list[str]]


_MIN_QUOTED_STRING_LEN = 2


def _parse_scalar(value: str) -> typing.Any:  # noqa: PLR0911
    stripped = value.strip()
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    if stripped == "null":
        return None
    if re.fullmatch(r"-?\d+", stripped):
        try:
            return int(stripped)
        except ValueError:
            return stripped
    if re.fullmatch(r"-?\d+\.\d+", stripped):
        try:
            return float(stripped)
        except ValueError:
            return stripped
    if (
        (stripped.startswith('"') and stripped.endswith('"'))
        or (stripped.startswith("'") and stripped.endswith("'"))
    ) and len(stripped) >= _MIN_QUOTED_STRING_LEN:
        return stripped[1:-1]
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return []
        parts = [part.strip() for part in inner.split(",")]
        result: list[str] = []
        for part in parts:
            parsed = _parse_scalar(part)
            parsed_str = str(parsed).lstrip("#")
            if parsed_str.strip():
                result.append(parsed_str)
        return result
    return stripped


def _yaml_scalar(value: typing.Any) -> str:  # noqa: PLR0911
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if not value:
            return '""'
        if re.search(r"[:\[\]{}#,\n\r\t]|^\s|\s$", value):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return json.dumps(value, ensure_ascii=True)


def _strip_tag_prefix(tag: str) -> str:
    cleaned = tag.strip()
    if cleaned.startswith("#"):
        return cleaned[1:]
    return cleaned


_FRONTMATTER_BLOCK_RE = re.compile(r"\A---\n(?P<fm>[\s\S]*?)\n---(?P<rest>[\s\S]*)\Z")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(.*)$")


def _split_frontmatter_block(content: str) -> tuple[list[str], str, bool]:
    match = _FRONTMATTER_BLOCK_RE.match(content)
    if not match:
        return [], content, False
    frontmatter_text = match.group("fm")
    rest = match.group("rest")
    frontmatter_lines = frontmatter_text.split("\n") if frontmatter_text else []
    return frontmatter_lines, rest, True


def _rebuild_note_with_frontmatter(  # noqa: PLR0911
    frontmatter_lines: list[str],
    rest: str,
    had_frontmatter: bool,
) -> str:
    if not frontmatter_lines:
        if not had_frontmatter:
            return rest
        if rest.startswith("\n"):
            return rest[1:]
        return rest

    fm = "\n".join(frontmatter_lines)
    if had_frontmatter:
        return f"---\n{fm}\n---{rest}"
    if not rest:
        return f"---\n{fm}\n---\n"
    if rest.startswith("\n"):
        return f"---\n{fm}\n---{rest}"
    return f"---\n{fm}\n---\n\n{rest}"


def _body_from_frontmatter_rest(rest: str) -> str:
    if rest.startswith("\n"):
        return rest[1:]
    return rest


def _find_frontmatter_key_span(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[int, int] | None:
    for i, line in enumerate(frontmatter_lines):
        match = _FRONTMATTER_KEY_RE.match(line)
        if not match:
            continue
        if match.group(1).strip() != key:
            continue
        j = i + 1
        while j < len(frontmatter_lines):
            if _FRONTMATTER_KEY_RE.match(frontmatter_lines[j]):
                break
            j += 1
        return i, j
    return None


def _parse_frontmatter_value_from_span(span_lines: list[str]) -> typing.Any:
    if not span_lines:
        return None
    match = _FRONTMATTER_KEY_RE.match(span_lines[0])
    if not match:
        return None
    inline_value = match.group(2).strip()
    if inline_value:
        return _parse_scalar(inline_value)

    list_items: list[typing.Any] = []
    for line in span_lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lstripped = line.lstrip()
        if lstripped.startswith("- "):
            list_items.append(_parse_scalar(lstripped[2:].strip()))
            continue
        return "\n".join(span_lines[1:]).strip()
    if list_items:
        return list_items
    return None


def _serialize_frontmatter_entry(key: str, value: typing.Any) -> list[str]:
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        lines = [f"{key}:"]
        lines.extend(f"  - {_yaml_scalar(item)}" for item in value)
        return lines
    return [f"{key}: {_yaml_scalar(value)}"]


def _set_frontmatter_key_lines(
    frontmatter_lines: list[str],
    key: str,
    value: typing.Any,
) -> list[str]:
    replacement = _serialize_frontmatter_entry(key, value)
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return frontmatter_lines + replacement
    start, end = span
    return frontmatter_lines[:start] + replacement + frontmatter_lines[end:]


def _delete_frontmatter_key_lines(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[list[str], bool]:
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return frontmatter_lines, False
    start, end = span
    updated = frontmatter_lines[:start] + frontmatter_lines[end:]
    while updated and not updated[0].strip():
        updated = updated[1:]
    while updated and not updated[-1].strip():
        updated = updated[:-1]
    return updated, True


def _get_frontmatter_key_value(
    frontmatter_lines: list[str],
    key: str,
) -> tuple[typing.Any, bool]:
    span = _find_frontmatter_key_span(frontmatter_lines, key)
    if span is None:
        return None, False
    start, end = span
    value = _parse_frontmatter_value_from_span(frontmatter_lines[start:end])
    return value, True


def _collect_inline_tags(body: str) -> list[str]:
    tags = re.findall(r"(?<![\w/#])#([A-Za-z0-9_\-/]+)", body)
    return list(dict.fromkeys(tag for tag in tags if tag))


def _remove_inline_tags(body: str, tags_to_remove: set[str]) -> str:
    updated = body
    for tag in tags_to_remove:
        rx = re.compile(rf"(^|[^\w#-])#{re.escape(tag)}\b", re.MULTILINE)
        updated = rx.sub(r"\1", updated)
    updated = re.sub(r"[ \t]+\n", "\n", updated)
    return re.sub(r"\n{3,}", "\n\n", updated)


async def _patch_entire_note(
    settings: Settings,
    path: str,
    expected_hash: str,
    original_content: str,
    new_content: str,
) -> dict[str, typing.Any]:
    total_lines = len(original_content.splitlines())
    end_line = total_lines if total_lines > 0 else 1
    return await do_patch_note_lines(
        settings,
        {
            "path": path,
            "start_line": 1,
            "end_line": end_line,
            "replacement": new_content,
            "expected_hash": expected_hash,
        },
    )


async def do_manage_frontmatter(  # noqa: PLR0911
    settings: Settings,
    args: ManageFrontmatterArgs,
) -> dict[str, typing.Any]:
    path = args["path"]
    operation = args["operation"]
    key = args["key"].strip()
    if not key:
        return {"error": "key is required"}

    read_result = await do_read_note_with_hash(settings, path)
    if "error" in read_result:
        return read_result

    content = str(read_result.get("content", ""))
    content_hash = read_result.get("content_hash")
    if not isinstance(content_hash, str) or not content_hash:
        return {"error": "Note read did not return content_hash"}

    frontmatter_lines, rest, had_frontmatter = _split_frontmatter_block(content)

    if operation == "get":
        value, exists = _get_frontmatter_key_value(frontmatter_lines, key)
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "value": value,
            "exists": exists,
        }

    if operation == "set":
        if "value" not in args:
            return {"error": "value is required for set operation"}
        value = args["value"]
        if key == "tags" and isinstance(value, list):
            value = [
                _strip_tag_prefix(str(tag))
                for tag in value
                if _strip_tag_prefix(str(tag))
            ]
        updated_frontmatter_lines = _set_frontmatter_key_lines(
            frontmatter_lines,
            key,
            value,
        )
        new_content = _rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            return patch_result
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "value": value,
        }

    if operation == "delete":
        updated_frontmatter_lines, deleted = _delete_frontmatter_key_lines(
            frontmatter_lines,
            key,
        )
        if not deleted:
            return {
                "path": path,
                "operation": operation,
                "key": key,
                "deleted": False,
            }
        new_content = _rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            return patch_result
        return {
            "path": path,
            "operation": operation,
            "key": key,
            "deleted": True,
        }

    return {"error": f"Invalid operation: {operation}"}


async def do_manage_tags(  # noqa: PLR0911, PLR0912, PLR0914
    settings: Settings,
    args: ManageTagsArgs,
) -> dict[str, typing.Any]:
    path = args["path"]
    operation = args["operation"]
    raw_tags = args.get("tags", [])
    normalized_tags = [
        _strip_tag_prefix(tag) for tag in raw_tags if _strip_tag_prefix(tag)
    ]

    read_result = await do_read_note_with_hash(settings, path)
    if "error" in read_result:
        return read_result

    content = str(read_result.get("content", ""))
    content_hash = read_result.get("content_hash")
    if not isinstance(content_hash, str) or not content_hash:
        return {"error": "Note read did not return content_hash"}

    frontmatter_lines, rest, had_frontmatter = _split_frontmatter_block(content)
    body = _body_from_frontmatter_rest(rest)
    frontmatter_tags_raw, has_frontmatter_tags = _get_frontmatter_key_value(
        frontmatter_lines,
        "tags",
    )
    if not has_frontmatter_tags:
        frontmatter_tags_raw = []
    if isinstance(frontmatter_tags_raw, list):
        frontmatter_tags = [
            _strip_tag_prefix(str(tag))
            for tag in frontmatter_tags_raw
            if _strip_tag_prefix(str(tag))
        ]
    elif isinstance(frontmatter_tags_raw, str):
        frontmatter_tags = (
            [_strip_tag_prefix(frontmatter_tags_raw)]
            if _strip_tag_prefix(frontmatter_tags_raw)
            else []
        )
    else:
        frontmatter_tags = []
    inline_tags = _collect_inline_tags(body)
    current_tags = list(dict.fromkeys(frontmatter_tags + inline_tags))

    if operation == "list":
        return {
            "path": path,
            "operation": operation,
            "tags": current_tags,
        }

    if not normalized_tags:
        return {"error": "tags is required for add/remove"}

    if operation == "add":
        merged = list(dict.fromkeys(frontmatter_tags + normalized_tags))
        updated_frontmatter_lines = _set_frontmatter_key_lines(
            frontmatter_lines,
            "tags",
            merged,
        )
        new_content = _rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            return patch_result
        return {
            "path": path,
            "operation": operation,
            "added": [tag for tag in normalized_tags if tag not in frontmatter_tags],
            "tags": merged,
        }

    if operation == "remove":
        to_remove = set(normalized_tags)
        updated_frontmatter_tags = [
            tag for tag in frontmatter_tags if tag not in to_remove
        ]
        updated_frontmatter_lines = frontmatter_lines
        if updated_frontmatter_tags:
            updated_frontmatter_lines = _set_frontmatter_key_lines(
                updated_frontmatter_lines,
                "tags",
                updated_frontmatter_tags,
            )
        else:
            updated_frontmatter_lines, _ = _delete_frontmatter_key_lines(
                updated_frontmatter_lines,
                "tags",
            )
        updated_body = _remove_inline_tags(body, to_remove)
        updated_rest = f"\n{updated_body}" if rest.startswith("\n") else updated_body
        new_content = _rebuild_note_with_frontmatter(
            updated_frontmatter_lines,
            updated_rest,
            had_frontmatter,
        )
        patch_result = await _patch_entire_note(
            settings,
            path,
            content_hash,
            content,
            new_content,
        )
        if "error" in patch_result:
            return patch_result
        final_tags = list(
            dict.fromkeys(updated_frontmatter_tags + _collect_inline_tags(updated_body))
        )
        return {
            "path": path,
            "operation": operation,
            "removed": [tag for tag in normalized_tags if tag in current_tags],
            "tags": final_tags,
        }

    return {"error": f"Invalid operation: {operation}"}


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
        return {
            "error": "No active search session. Call dragonglass_new_search_session first."
        }

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
    session = get_current_session() or new_session()

    path = args["path"]
    resolved_expected_hash = args["expected_hash"] or session.get_last_read_hash(path)
    if not resolved_expected_hash:
        return {
            "error": (
                "No stored hash for this file. Call dragonglass_read_note_with_hash(path) before "
                "dragonglass_patch_note_lines(path, ...)."
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
        session = new_session()
        emit_tool_event(
            "dragonglass_new_search_session",
            "done",
            "New search session",
            f"id={session.id}",
        )
        return {"session_id": session.id, "status": "created"}

    @m.tool(name="dragonglass_keyword_search")
    async def keyword_search(
        queries: _StringList | None = None,
        query: str | None = None,
    ) -> dict[str, typing.Any]:
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
        result = await _do_keyword_search(settings, queries)
        elapsed = time.monotonic() - started
        terms = ", ".join(str(q) for q in queries)
        phase = "error" if "error" in result else "done"
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"{result.get('total_found', 0)} files found ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_keyword_search",
            phase,
            f"Keyword search: {terms}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_vector_search")
    async def vector_search(
        query: str, top_n: int = 10, min_score: float = 0.35
    ) -> list[dict[str, typing.Any]]:
        """Perform semantic (vector) search to find notes by meaning.

        Args:
            query: a natural language description of what you are looking for.
            top_n: maximum number of results to return (default: 10).
            min_score: minimum similarity score [0..1] (default: 0.35).
        """
        started = time.monotonic()
        result = await _do_vector_search(settings, query, top_n, min_score)
        elapsed = time.monotonic() - started
        errs = [item.get("error") for item in result if isinstance(item, dict)]
        errs = [e for e in errs if isinstance(e, str)]
        phase = "error" if errs else "done"
        detail = (
            _safe_value_preview(errs[0])
            if errs
            else f"{len(result)} hits ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_vector_search",
            phase,
            f"Vector search: {_safe_value_preview(query, 80)}",
            detail,
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
                        "done",
                        f"Run command: {_safe_value_preview(command_id)}",
                        "ok",
                    )
                    return {"status": "executed", "command_id": command_id}
                emit_tool_event(
                    "dragonglass_run_command",
                    "error",
                    f"Run command: {_safe_value_preview(command_id)}",
                    f"HTTP {resp.status_code}",
                )
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            logger.exception("run_command failed for %r", command_id)
            emit_tool_event(
                "dragonglass_run_command",
                "error",
                f"Run command: {_safe_value_preview(command_id)}",
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
        started = time.monotonic()
        result = await do_read_note_with_hash(settings, path, start_line, end_line)
        elapsed = time.monotonic() - started
        phase = "error" if "error" in result else "done"
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
        phase = "error" if "error" in result else "done"
        detail = (
            _safe_value_preview(result.get("error"))
            if "error" in result
            else f"ok ({elapsed:.2f}s)"
        )
        emit_tool_event(
            "dragonglass_patch_note_lines",
            phase,
            f"Patching: {_safe_value_preview(path, 60)} lines {start_line}-{end_line}",
            detail,
        )
        return result

    @m.tool(name="dragonglass_manage_frontmatter")
    async def manage_frontmatter(
        path: str,
        operation: typing.Literal["get", "set", "delete"],
        key: str,
        value: typing.Any = None,
    ) -> dict[str, typing.Any]:
        """Get, set, or delete a frontmatter key."""
        started = time.monotonic()
        args: ManageFrontmatterArgs = {
            "path": path,
            "operation": operation,
            "key": key,
        }
        if operation == "set":
            args["value"] = value
        result = await do_manage_frontmatter(settings, args)
        elapsed = time.monotonic() - started
        phase = "error" if "error" in result else "done"
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
    ) -> dict[str, typing.Any]:
        """Add, remove, or list note tags."""
        started = time.monotonic()
        args: ManageTagsArgs = {
            "path": path,
            "operation": operation,
        }
        if tags is not None:
            args["tags"] = tags
        result = await do_manage_tags(settings, args)
        elapsed = time.monotonic() - started
        phase = "error" if "error" in result else "done"
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
